import os
import yaml
import asyncio
import discord
import schedule
import argparse
import datetime
from dotenv import load_dotenv
from discord.ext import commands

print("Starting..")

load_dotenv() 
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='.', description='A Studium Bot to manage Studying')
   
# https://discordpy.readthedocs.io/en/latest/api.html#discord.TextChannel
# https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild

messagesToSend = []

async def showHelpWrapper(ctx, title, val):
    embedVar = discord.Embed(color=0x00ff00)
    embedVar.add_field(
        name=title, 
        value=val, 
        inline=False)
    await ctx.send(embed=embedVar)

async def addScheduleString(str, ctx = None) -> bool:
  
    def split(str):
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

    str = str.replace('on', '-on').replace('at', '-at').replace('send', '-send')

    if '-h' in str or '-help' in str:
        await showHelp(None)
        return False
        
    try:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('-on', dest='on')
        parser.add_argument('-at', dest='at')
        parser.add_argument('-send', dest='send', required=True)
        args = parser.parse_args(split(str))

        with open("schedule.yaml", 'r') as stream:
            for line in stream.readlines():
                if (f'on {args.on}' in line and f'at {args.at}' in line) or \
                (f'on {args.on}' in line and args.at == None) or \
                (args.on == None and f'at {args.at}' in line):
                    if ctx != None:
                        await ctx.send('Theres already something scheduled at that time, please select another Timepoint.')
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
                await showHelp('Day not recognized!')
                
        if args.at != None:
            date = datetime.datetime.strptime(args.at, '%H:%M')
            time = date - datetime.timedelta(hours=1)
            if time.hour > date.hour:
                await showHelp('Hour must be greater than 1 (Sorry)')
                return False

            event = event.at(time.strftime('%H:%M'))
        
        def job(str):
            print("Event happended:", str)
            messagesToSend.append(str)

        event.do(job, args.send)
        print("added:")
        print(args)

        return True

    except Exception as e:
        await showHelp('Exception occured (Sorry)')
        print(e)
        return False

async def reload():
    schedule.clear()

    with open("schedule.yaml", 'r') as stream:
        for line in stream.readlines():
            if line.strip() != '':
                await addScheduleString(line)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you.."))
    print('We have logged in as', bot.user)
    # Load from File
    # TODO based on server ID
    await reload()

class Studium(commands.Cog):
    """Category documentations"""

    def __init__(self):
        if not os.path.exists("schedule.yaml"):
            with open("schedule.yaml", 'w+') as stream:
                pass

    @commands.command(name='add', help='This Command adds a message to be displayed at a specific time!')
    async def addToSchedule(self, ctx, *, arg):
        print("add")
        # Add to Schedule
        added = await addScheduleString(arg, ctx)

        if added == True:
            # Save to File
            with open("schedule.yaml", 'a') as stream:
                stream.write(arg)
                stream.write('\n')
            await ctx.send('Added!')
        else:
            await ctx.send('Failed to Add!')

    @commands.command(name='list', help='Lists all running schedules')
    async def list(self, ctx):
        print("list")

        embedVar = discord.Embed(title="Schedules", color=0x00ff00)
        with open("schedule.yaml", 'r') as stream:
            for line in stream.readlines():
                if line.strip() != '':
                    embedVar.add_field(name="Schedule:", value=line, inline=False)
        await ctx.send(embed=embedVar)

    @commands.command(name='clear', help='Clears all running schedules')
    async def clear(self, ctx):
        print("clear")
        with open("schedule.yaml", 'w+') as stream:
            pass
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
        
        with open("schedule.yaml", 'r') as stream:
            lines = stream.readlines()

        idx = int(arg) if arg.isdigit() else None
        removed = False
        with open("schedule.yaml", 'w+') as stream:
            for i, line in enumerate(lines):
                if idx != i and line.strip() != arg.strip():
                    if line.strip() != '':
                        stream.write(line)
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
        with open("schedule.yaml", 'r') as stream:
            for line in stream.readlines():
                if line.strip() != '':
                    data += '.add ' + line

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
bot.add_cog(Studium())
bot.add_cog(Util())
bot.run(TOKEN)