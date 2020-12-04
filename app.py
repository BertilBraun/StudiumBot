import os
import re
import io
import random
import asyncio
import discord
import requests
import schedule
import argparse
import datetime
import urllib.request
import urllib.parse

from PIL import Image
from dotenv import load_dotenv
from discord.ext import commands

print("Starting..")

load_dotenv() 
TOKEN = os.getenv('DISCORD_TOKEN')

URL = 'http://studium-bot.braun-oliver.de/studium-bot.php'

bot = commands.Bot(command_prefix='.', description='A Studium Bot to manage Studying')
   
# https://discordpy.readthedocs.io/en/latest/api.html#discord.TextChannel
# https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild

messagesToSend = []

def getSchedules():
    r = requests.get(URL)
    return [line for line in r.text.split('\n') if line.strip() != '']

async def showHelpWrapper(ctx, title, val):
    embedVar = discord.Embed(color=0x00ff00)
    embedVar.add_field(
        name=title, 
        value=val, 
        inline=False)
    await ctx.send(embed=embedVar)

async def addScheduleString(str, ctx = None, checkIfExists = False) -> bool:
  
    def split(str):
        def replace(m):
            if m.group().startswith('"'):
                return m.group()
            return m.group().replace('on', '-on').replace('at', '-at').replace('send', '-send')

        str = re.sub(r'"[^"]*"|[^"]+', replace, str)
        ret = []
        o = ""
        doubleOpen = False
        singleOpen = False

        for c in str:
            if c == '"':
                doubleOpen = not doubleOpen
            elif c == "'":
                singleOpen = not singleOpen
            elif c == ' ' and not singleOpen and not doubleOpen:
                ret.append(o)
                o = ""
            else:
                o += c

        return ret + [o]
    
    async def showHelp(error):
        if ctx == None:
            return

        title =  "Error in Command: Add " + error if (error != None) else "Help for: Add"
        val = """
            usage: .add [-h | -help] on ... at ... send ...

            optional arguments:
            -h -help show this help message and exit
            on      : Which Day? One of [Mo, [Tu | Di], [We | Mi], [Th | Do], Fr, Sa, [Su | So], every]
            at      : What Time? Format like 18:10
            required arguments:
            send    : What to Send? "New Event upcoming! Join us in VC!"

            example command:
            .add on Mo at 18:10 send "New Event upcoming! Join us in VC!"
            """
        await showHelpWrapper(ctx, title, val)

    if '-h' in str or '-help' in str:
        await showHelp(None)
        return False
        
    try:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('-on', dest='on')
        parser.add_argument('-at', dest='at')
        parser.add_argument('-send', dest='send', required=True)
        args = parser.parse_args(split(str))

        if checkIfExists:
            for line in getSchedules():
                if (f'on {args.on}' in line and f'at {args.at}' in line) or \
                (f'on {args.on}' in line and args.at == None) or \
                (args.on == None and f'at {args.at}' in line):
                    if ctx != None:
                        await ctx.send('Theres already something scheduled at that time, please select another Timepoint.')
                    print('Theres already something scheduled at that time, please select another Timepoint.')
                    return False

        event = schedule.every()

        if args.on != None:
            # [Mo, [Tu | Di], [We | Mi], [Th | Do], Fr, Sa, [Su | So], every]
            if args.on == 'Mo':
                event = event.monday
            elif args.on == 'Tu' or args.on == 'Di':
                event = event.tuesday
            elif args.on == 'We' or args.on == 'Mi':
                event = event.wednesday
            elif args.on == 'Th' or args.on == 'Do':
                event = event.thursday
            elif args.on == 'Fr':
                event = event.friday
            elif args.on == 'Sa':
                event = event.saturday
            elif args.on == 'Su' or args.on == 'So':
                event = event.sunday
            elif args.on == 'every':
                event = event.day
            else:
                print('Day not recognized!')
                await showHelp('Day not recognized!')
                
        if args.at != None:
            date = datetime.datetime.strptime(args.at, '%H:%M')
            time = date - datetime.timedelta(hours=1)
            if time.hour > date.hour:
                await showHelp('Hour must be greater than 1 (Sorry)')
                print('Hour must be greater than 1 (Sorry)')
                return False

            event = event.at(time.strftime('%H:%M'))
        
        def job(str):
            print("Event happended:", str)
            messagesToSend.append(str)

        event.do(job, args.send)
        print("added:", args)

        return True

    except Exception as e:
        await showHelp('Exception occured (Sorry)')
        print(e)
        return False

async def reload():
    schedule.clear()

    for line in getSchedules():
        if line.strip() != '':
            await addScheduleString(line)

# Using 3rdparty site to render TeX is not
# the best solution, however CodeCogs site
# is pretty stable and this method does not
# require installing LaTeX on local machine.
async def generate_file(dpi, tex):
    MARGIN = 20
    URL = 'https://latex.codecogs.com/gif.latex?{0}'
    TEMPLATE = '\\dpi{{{}}} \\bg_grey {}'
    query = TEMPLATE.format(dpi, tex)
    url = URL.format(urllib.parse.quote(query))
    bytes = urllib.request.urlopen(url).read()
    img = Image.open(io.BytesIO(bytes))
    old_size = img.size
    new_size = (old_size[0] + MARGIN, old_size[1] + MARGIN)
    new_img = Image.new("RGB", new_size, (255, 255, 255))
    new_img.paste(img, (int(MARGIN / 2), int(MARGIN / 2)))
    img_bytes = io.BytesIO()
    new_img.save(img_bytes, 'PNG')
    img_bytes.seek(0)
    return img_bytes

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you.."))
    print('We have logged in as', bot.user)
    # Load from File
    # TODO based on server ID
    await reload()

class Schedule(commands.Cog):
    """Category documentations"""

    @commands.command(name='add', help='This Command adds a message to be displayed at a specific time!')
    async def addToSchedule(self, ctx, *, arg: str):
        print("add", len(arg.splitlines()))
        
        # Add to Schedule
        for line in arg.splitlines(False):
            line = line.strip('.add ')

            added = await addScheduleString(line, ctx, True)

            if added == True:
                # Save to File
                requests.post(URL, data = {'schedule':line.strip() + '\n' })
                await ctx.send('Added!')

        await ctx.send('Done!')

    @commands.command(name='list', help='Lists all running schedules')
    async def list(self, ctx):
        print("list")

        embedVar = discord.Embed(title="Schedules", color=0x00ff00)

        def search(line:str):
            d = { 
                'Mo': 1, 
                'Tu': 2, 'Di': 2,
                'We': 3, 'Mi': 3,
                'Th': 4, 'Do': 4,
                'Fr': 5,
                'Sa': 6,
                'Su': 7, 'So': 7,
                'every': 8,
                }
            tokens = line.split()
            key = ''
            if 'on' in tokens:
                key += str(d[tokens[tokens.index('on') + 1]])
            if 'at' in tokens:
                key += ' ' + tokens[tokens.index('at') + 1].rjust(5, '0')
            return key
        
        lines = getSchedules()
        lines.sort(key=search)

        schedules = {}
        for line in lines:
            if not 'on' in line:
                if not 'On Time' in schedules:
                    schedules['On Time'] = []
                schedules['On Time'].append(line)
            else:
                tokens = line.split()
                idx = tokens.index('on')
                key = 'On ' + tokens[idx + 1]
                tokens = tokens[:idx] + tokens[idx + 2:]
                if not key in schedules:
                    schedules[key] = []
                schedules[key].append(' '.join(tokens))
                
        for k, v in schedules.items():
            embedVar.add_field(name=k, value='\n'.join(v), inline=False)
        await ctx.send(embed=embedVar)

    @commands.command(name='clear', help='Clears all running schedules')
    async def clear(self, ctx):
        print("clear")
        requests.post(URL, data = {'clear':'true'})
        schedule.clear()
        await ctx.send("Cleared Schedule!")

    @commands.command(name='rem', help='Removes a schedule')
    async def rem(self, ctx, *, arg):
        print("rem")

        if '-h' in arg or '-help' in arg:
            title =  "Help for: Rem"
            val = """
                usage: .rem [-h | -help] idx | str

                optional arguments:
                -h -help show this help message and exit
                required arguments:
                idx     : Index of schedule to be removed (0 based)
                str     : String representation of schedule to be removed

                example command:
                .rem 0
                .rem on Mo at 18:10 send "New Event upcoming! Join us in VC!"
                """
            await showHelpWrapper(ctx, title, val)
            return
        
        lines = getSchedules()
        requests.post(URL, data = {'clear':'true'})

        idx = int(arg) if arg.isdigit() else None
        removed = False
        for i, line in enumerate(lines):
            if idx != i and line != arg.strip():
                requests.post(URL, data = {'schedule':line + '\n'})
            else:
                await ctx.send("Removed from Schedule!")
                removed = True

        if not removed:
            await ctx.send("Nothing Removed from Schedule!")
                    
        # reload remaining schedules
        await reload()
        
    @commands.command(name='reload', help='Reload all Schedules from File')
    async def reload(self, ctx):
        print("reload")
        await reload()
        await ctx.send("Reloaded Schedule!")
         
    @commands.command(name='dump', help='Dumps all Schedules to Chat')
    async def dump(self, ctx):
        print("dump")     

        data = ''
        for line in getSchedules():
            data += '.add ' + line + '\n'

        embedVar = discord.Embed(color=0x00ff00)   
        embedVar.add_field(
            name="Schedule Dump", 
            value=data, 
            inline=False)
        await ctx.send(embed=embedVar)

    @commands.command(name='setup', help='Setup the Bot')
    async def setup(self, ctx):
        print("setup")
        # TODO set channel
        # TODO set prefix
        pass

class Util(commands.Cog):
    @commands.command(name='display', help='Display information about Server')
    async def display(self, ctx):
        print("display")

        embedVar = discord.Embed(title="Discord Data", color=0x00ff00)
        embedVar.add_field(
            name="Guild", 
            value=str(ctx.guild) + ' ' + str(ctx.guild.id), 
            inline=False)
        embedVar.add_field(
            name="Channel", 
            value=str(ctx.channel) + ' ' + str(ctx.channel.id), 
            inline=False)
        embedVar.add_field(
            name="Author", 
            value=str(ctx.author) + ' ' + str(ctx.me), 
            inline=False)
        await ctx.send(embed=embedVar)
        
    @commands.command(name='clearchat', help='Clears Messages of current channel')
    async def clearchat(self, ctx, number = None):
        print("clearchat")

        number = 1000 if number == None else int(number) + 1
        await ctx.channel.purge(limit=number)
        
    @commands.command(name='hol', help='Pings provided User in each channel')
    async def hol(self, ctx, user):
        print("hol")

        for channel in ctx.guild.text_channels:
            await channel.send("Komm mal her " + user + "!")
            
    @commands.command(name='latex', help='Renderes the entered Calculation based on Latex format')
    async def latex(self, ctx, *, calculation):
        print("latex", calculation)
        await ctx.message.delete()
        bytes = await generate_file(200, calculation)
        filename = '{}.png'.format(calculation)
        await ctx.message.channel.send(f'***{ctx.message.author.name}***\n.latex {calculation}', file=discord.File(bytes, filename=filename))
         
async def loop():
    while True:
        # Channel bot-notifications
        # TODO Based on server ID -> also only send messages that are supposed to go to that server
        schedule.run_pending()

        channel = bot.get_channel(772952750668382238)

        for str in messagesToSend:
            print("sending", str)
            await channel.send(str)

        messagesToSend.clear()
        
        # sleep until next minute starts
        now = datetime.datetime.now()
        lastMin = now.replace(second=5)
        seconds = max((now - lastMin).seconds, 0)
        # sleep full minute - seconds passed in this minute
        # await asyncio.sleep(60 - seconds)
        await asyncio.sleep(1)


bot.loop.create_task(loop())
bot.add_cog(Schedule())
bot.add_cog(Util())
bot.run(TOKEN)
