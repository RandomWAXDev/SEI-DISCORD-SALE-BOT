import discord
from discord.ext import tasks, commands
from discord import Intents
import requests
from datetime import datetime, timezone
from PIL import Image
from io import BytesIO

TOKEN = 'CHANGEME' #CHANGE THIS TO YOUR SESSION TOKEN
CHANNEL_ID = CHANGEME #CHANGE ME TO THE SEINSEI-SALES CHANNEL ID DONT ENCAP. RAW VALUE ONLY

intents = Intents.all()

bot = commands.Bot(command_prefix='!', intents=intents)

nft_address_to_track = "sei1vjgrptlrm0alx330lv6260kzewv7p8elpputvedd45sxrtel2v5qzkrcd7" #CHANGE THIS TO SEINSEI COLLECTION ADDRESS!!

api_url = "https://api.prod.pallet.exchange/api/v1/marketplace/activities"

last_timestamp = datetime.now(timezone.utc)

def fetch_data():
    params = {
        'page': 1,
        'page_size': 1000,
        'chain_id': 'pacific-1',
        'nft_address': nft_address_to_track,
        'event_type': 'sale'
    }

    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data['activities']
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None

async def process_data():
    global last_timestamp

    activities = fetch_data()

    if activities:
        new_data = [activity for activity in activities if datetime.fromisoformat(activity['ts']).replace(tzinfo=timezone.utc) > last_timestamp]

        if new_data:
            sorted_data = sorted(new_data, key=lambda x: (x['token']['name'], float(x['price_value'])))

            last_timestamp = datetime.fromisoformat(sorted_data[-1]['ts']).replace(tzinfo=timezone.utc)

            channel = bot.get_channel(CHANNEL_ID)

            for activity in sorted_data:
                seller_domain = activity['seller_info']['domain'] if activity['seller_info']['domain'] else ""
                buyer_domain = activity['buyer_info']['domain'] if activity['buyer_info']['domain'] else ""
                
                price_in_sei = int(activity['price'][0]['amount']) / 1_000_000_000 * 1000
                
                image_url = activity['token']['image']
                image_data = requests.get(image_url).content
                img = Image.open(BytesIO(image_data))
                img = img.resize((300, 300))
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                embed = discord.Embed(
                    title=f"New Sale: {activity['token']['name']}",
                    description=f"**Seller:** {seller_domain} {activity['seller']} \n"
                                f"**Buyer:** {buyer_domain} {activity['buyer']} \n"
                                f"**Sale Price:** {price_in_sei:.4f} SEI",
                    color=discord.Color.green(),
                )
                embed.set_thumbnail(url="attachment://token_image.png")
                await channel.send(embed=embed, file=discord.File(img_bytes, "token_image.png"))
#THIS SECTION IS FOR TESTING PURPOSES. YOU CAN EITHER COMMENT IT OUT OR DELETE IT!!
@bot.command(name='lastsale')
async def last_sale(ctx):
    activities = fetch_data()

    if activities:
        sorted_data = sorted(activities, key=lambda x: datetime.fromisoformat(x['ts']).replace(tzinfo=timezone.utc))

        last_sale = sorted_data[-1]

        seller_domain = last_sale['seller_info']['domain'] if last_sale['seller_info']['domain'] else ""
        buyer_domain = last_sale['buyer_info']['domain'] if last_sale['buyer_info']['domain'] else ""
        price_in_sei = int(last_sale['price'][0]['amount']) / 1_000_000_000 * 1000  # Multiply by 1000 to get the real price

        image_url = last_sale['token']['image']
        image_data = requests.get(image_url).content
        img = Image.open(BytesIO(image_data))
        img = img.resize((300, 300))
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        embed = discord.Embed(
            title=f"Last Sale: {last_sale['token']['name']}",
            description=f"**Seller:** {seller_domain} {last_sale['seller']} \n"
                        f"**Buyer:** {buyer_domain} {last_sale['buyer']} \n"
                        f"**Sale Price:** {price_in_sei:.4f} SEI",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url="attachment://token_image.png")
        await ctx.send(embed=embed, file=discord.File(img_bytes, "token_image.png"))
    else:
        await ctx.send("Failed to fetch data.")

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    data_check.start()

@tasks.loop(seconds=10) #YOU CAN CHANGE THIS VALUE TO ANYTHING, I SET FOR 10 SECONDS FOR API RESTRICTIONS
async def data_check():
    await process_data()

bot.run(TOKEN)
