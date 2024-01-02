import discord
import sqlite3
import random
import asyncio 
import schedule
import requests

from datetime import datetime, timedelta 
from discord.ui import Button, View
from discord.ext import commands
from pytz import timezone
from dico_token import Token

from openpyxl import load_workbook, Workbook

intents = discord.Intents.all()
intents.messages = True  # 메시지 관련 intent를 활성화
intents.guilds = True    # 서버 관련 intent를 활성화
intents.members = True    # 서버 멤버 정보를 받아오기 위해 필요한 권한 설정

bot = commands.Bot( command_prefix='!', intents=intents)



@bot.event
async def on_ready():
    # user_database.db에 users 테이블 생성 또는 연결
    conn_user = sqlite3.connect('user_database.db')
    cursor_user = conn_user.cursor()
    cursor_user.execute('''
    CREATE TABLE IF NOT EXISTS users (
	"user_id"	INTEGER,
	"username"	TEXT,
	"nickname"	TEXT,
	"last_fortune_date"	TEXT,
	"last_attend_date"	TEXT,
	"is_logged_in"	INTEGER,
	"fortune_count"	INTEGER,
	"coin_creation_count" INTEGER  DEFAULT 1,
	"fortune"	TEXT,
	PRIMARY KEY("user_id","username")
)
    ''')
    conn_user.commit()

    

    cursor_user.execute('''
       CREATE TABLE IF NOT EXISTS coins (
	"user_id"	INTEGER,
	"username"	TEXT,
	"nickname"	TEXT,
	"last_date"	TEXT,
	"coins_count"	INTEGER DEFAULT 0,
	"cupon_count"	INTEGER DEFAULT 0,
	PRIMARY KEY("user_id","username")
)
    ''')
     
    conn_user.commit()

    



    print(f'Logged in as: {bot.user.name} - {bot.user.id}')
    channel_id = '내채널 Id'
    channel = bot.get_channel(channel_id)
    
    message = '```봇 작동중```'

    if channel:
        await channel.send(message)
        


# db 연결 반환

def connect_to_database(database_name):
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    return conn, cursor





    
#------------------------------------------------------유저가 존재하는 지 검사. 있으면 true, 없으면 false.
def is_user_registered(cursor, user_id):

    cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] > 0




#------------------------------------------------------유저가 로그인 했는지 검사. 했으면 true, 안했으면 false.
def get_login_status(cursor, user_id):
    cursor.execute('SELECT is_logged_in FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] == 1


#---------------------------------------------------------------------------------------------------------------------------------------------로그인 회원가입 인증 확인 및 문구 출력

async def chekAuthentication(ctx, cursor_user, user_id):
    
    if not is_user_registered(cursor_user, user_id):
        await ctx.send(f'{ctx.author.display_name}님, 회원가입을 먼저 해주세요! `!운명 회원가입` 명령어를 사용하세요.')
        #conn_user.close()
        return True
    
    if not is_user_logged_in(cursor_user, user_id):
        await ctx.send(f'{ctx.author.display_name}님, 로그인을 먼저 해주세요! `!운명 로그인` 명령어를 사용하세요.')
        #conn_user.close()
        return True

    return False



#--------------------------------------------------------------------------------------------------------------------------------------------

# register_user 함수의 정의
async def register_user(ctx):
    print(f'{ctx.author.name} 님 가입함. ')
    print(f'User ID: {ctx.author.id}')

    user_id = ctx.author.id
    user_name = ctx.author.name
    user_nickname = ctx.author.display_name
    
    conn_user, cursor_user = connect_to_database('user_database.db')
    
    
    # 이미 회원가입한 경우
    if is_user_registered(cursor_user, user_id):
        await ctx.send(f'{ctx.author.display_name}님, 이미 회원가입을 하셨습니다. `!오늘의운명` 명령어로 운명을 확인하세요.')
        conn_user.close()
        return
    new_fortune = generate_fortune()
    last_attend_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 회원가입 진행
    cursor_user.execute('INSERT INTO users(user_id, username, nickname, last_fortune_date, last_attend_date, is_logged_in, fortune_count, fortune) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (user_id, user_name, user_nickname, datetime.now().strftime('%Y-%m-%d'), last_attend_date, 0, 0, new_fortune))
    cursor_user.execute('INSERT INTO coins (user_id, username, nickname, last_date, coins_count, cupon_count) VALUES (?, ?, ?, ?, ?, ?)', (user_id, user_name, user_nickname, datetime.now().strftime('%Y-%m-%d'), 0, 0))

    conn_user.commit()
    await ctx.send(f'{ctx.author.display_name}님, 회원가입이 완료되었습니다!')
    conn_user.close()


async def login(ctx):
    user_id = ctx.author.id
    conn_user, cursor_user = connect_to_database('user_database.db')

    if not is_user_registered(cursor_user, user_id):
        await ctx.send(f'{ctx.author.display_name}님, 회원가입을 먼저 해주세요! `!운명 회원가입` 명령어를 사용하세요.')
        conn_user.close()
        return

    # 이미 로그인한 경우
    if is_user_logged_in(cursor_user, user_id):
        await ctx.send(f'{ctx.author.display_name}님, 이미 로그인되어 있습니다!')
        conn_user.close()
        return

    cursor_user.execute('UPDATE users SET is_logged_in = 1 WHERE user_id = ?', (user_id,))
    conn_user.commit()

    await ctx.send(f'{ctx.author.display_name}님, 로그인이 완료되었습니다!')
    conn_user.close()




def is_user_logged_in(cursor, user_id):
    cursor.execute('SELECT is_logged_in FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1





async def logout(ctx):
    user_id = ctx.author.id
    conn_user, cursor_user = connect_to_database('user_database.db')
    
    if(await chekAuthentication(ctx, cursor_user, user_id)):
       return
    
    cursor_user.execute('UPDATE users SET is_logged_in = 0 WHERE user_id = ?', (user_id,))
    conn_user.commit()

    await ctx.send(f'{ctx.author.display_name}님, 로그아웃이 완료되었습니다!')
    conn_user.close()

async def withdraw_user(ctx):
    user_id = ctx.author.id
    conn_user, cursor_user = connect_to_database('user_database.db')

    if not is_user_registered(cursor_user, user_id):
        await ctx.send(f'{ctx.author.display_name}님, 회원가입을 먼저 해주세요! `!운명 회원가입` 명령어를 사용하세요.')
        conn_user.close()
        return

    cursor_user.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    
    conn_user.commit()

    await ctx.send(f'{ctx.author.display_name}님, 회원 탈퇴가 완료되었습니다. 이용해주셔서 감사합니다!')
    conn_user.close()


#------------------------------------------------------------------------------------------------------------------------------------

@bot.command(name='운명')
async def fortune_command(ctx, action=None):





    
    if action == '회원가입':
        await register_user(ctx)
    elif action == '로그인':
        await login(ctx)
    elif action == '로그아웃':
        await logout(ctx)
    elif action == '회원탈퇴':
        await withdraw_user(ctx)
    elif action == '명령어':
        await getCommandF(ctx)
    elif action == '바꾸기':
        await change_fortune(ctx)
    elif action == '코인제작':
        await create_coin(ctx)
    elif action == '내코인':
        await select_coin(ctx)
    elif action == "출석체크":
        await attend_fortune(ctx)
    elif action == '관리자명령어':
        await adminCommandList(ctx)
    elif action == '티켓사용' :
        await use_cupon(ctx)
    elif action == '내티켓':
        await print_cupon_count(ctx)
    elif action == action is None :
        await fortune_telling(ctx)

    else:
        await ctx.send('잘못된 형식입니다. 다시 입력해 주세요!')





#--------------------------------------------------------------------------------------------------------------------------------------------코인지급 관리자




# 사용자가 등록되어 있는지 확인하는 함수
def user_exists(cursor_user, user_id):
    cursor_user.execute('SELECT user_id FROM coins WHERE user_id = ?', (user_id,))
    return cursor_user.fetchone() is not None

# 코인 갯수 증가 함수
def increase_coins(conn_user, cursor_user, user_id, count):
    cursor_user.execute('UPDATE coins SET coins_count = coins_count + ? WHERE user_id = ?', (count, user_id))
    conn_user.commit()

# 티켓 갯수 증가 함수
def increase_cupon(conn_user, cursor_user, user_id, count):
    cursor_user.execute('UPDATE coins SET cupon_count = cupon_count + ? WHERE user_id = ?', (count, user_id))
    conn_user.commit()


# 입력값으로 코인갯수 초기화    
def reset_coins(cursor_user, conn_user, user_id, count):
    
    cursor_user.execute('UPDATE coins SET coins_count = ? WHERE user_id = ?', (count, user_id))
    conn_user.commit()

def reset_date(conn_user, cursor_user, user_id, yestdate):
    
    cursor_user.execute('UPDATE coins SET last_date = ? WHERE user_id = ?', (yestdate, user_id))
    conn_user.commit()

#---------------------------------------------------------------------------------------------------------------------------------운명 변경

async def change_fortune(ctx):

    conn_user, cursor_user = connect_to_database('user_database.db')

    user_id = ctx.author.id
    
    if(await chekAuthentication(ctx, cursor_user, user_id)):
       return
    conn_user.commit()


    
    
    # 코인이 충분한지 확인
    if not has_enough_coins(cursor_user, user_id)[0]:
        await ctx.send("코인이 부족하여 운명을 바꿀 수 없습니다.")
        return

    # 코인 사용
    use_coins(conn_user, cursor_user, user_id, 1)

  
    # 바꾼 운명을 fortune 변수에 저장
    new_fortune = generate_fortune();
    remaining_coins = get_remaining_coins(cursor_user, user_id)
    
    update_user_fortune(conn_user, cursor_user, user_id, new_fortune)
    
    await ctx.send(f"```신비로운 코인의 힘으로 {ctx.author.display_name}님의 운명이 바뀌었습니다.\n코인 1개가 사용되었습니다. 남은 코인 : {remaining_coins}\n---------------------------------------------------------------------\n```")
    #{new_fortune}
    conn_user.close()



#------------------------------------------------------------------------------------------------------------------------------운명 업데이트
    
def update_user_fortune(conn_user, cursor_user, user_id, new_fortune):

    cursor_user.execute('SELECT fortune_count FROM users WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()

    
    if result is not None:
        fortune_count = int(result[0])

        # None 또는 빈 문자열인 경우 기본값으로 설정
        if fortune_count is None or fortune_count == '':
            fortune_count = 0
              
        today = datetime.now().strftime('%Y-%m-%d')
        cursor_user.execute('UPDATE users SET last_fortune_date = ?, fortune_count = ?, fortune = ? WHERE user_id = ?', (today, fortune_count + 1, new_fortune, user_id))
        conn_user.commit()

    else:
        # 적절한 처리, 예를 들면 로그 남기기, 기본값 설정 등을 수행할 수 있습니다.
        print(f"User with ID {user_id} not found. Cannot update fortune.")

    
 #------------------------------------------------------------------------------------------------------------------------------코인 갯수 0개면 false
    
def has_enough_coins(cursor_user, user_id):
    
    cursor_user.execute('SELECT coins_count FROM coins WHERE user_id = ?', (user_id,))
    coins = cursor_user.fetchone()

    if coins is not None and coins[0] >= 1:
        return True, coins[0]
    else:
        return False, 0

    
# 코인 갯수 업데이트 (뺴기)
def use_coins(conn_user, cursor_user, user_id, amount):
    cursor_user.execute('UPDATE coins SET coins_count = coins_count - ? WHERE user_id = ?', (amount, user_id))
    conn_user.commit()
    


def get_remaining_coins(cursor_user, user_id):
    cursor_user.execute('SELECT coins_count FROM coins WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()
    return result[0] if result else 0

#-------------------------------------------------------------------현재 코인 출력

async def select_coin(ctx):
    
    conn_user, cursor_user = connect_to_database('user_database.db')
    
    user_id = ctx.author.id


    if(await chekAuthentication(ctx, cursor_user, user_id)):
       return


    
    # 현재 코인 수 조회
    current_coins = has_enough_coins(cursor_user, user_id)[1]

    user_name = ctx.author.display_name

    await ctx.send(f"```{user_name}님, 현재 보유한 코인 수는 {current_coins}개입니다.```")

    conn_user.close()
#----------------------------------------------------------------------관리자 명령어


@bot.command(name='패치')
async def adminCom(ctx, type : str, user_id : str, count : int):

    
    if ctx.author.id == admin :
        conn_user, cursor_user = connect_to_database('user_database.db')
        if type=="적립" :
            
            increase_coins(conn_user, cursor_user, user_id, count)
            conn_user.commit()
            conn_user.close()
            print(f'{user_id}님에게 운명코인 {count}를 적립 시켰습니다. 관리자님.')
            await ctx.send('패치 완료!')
           
        elif type=="코인":
           reset_coins(cursor_user, conn_user, user_id, count)
           conn_user.commit()
           conn_user.close()
           print(f'{user_id}님의 운명코인을 {count}개로 초기화 시켰습니다. 관리자님.')
           await ctx.send('패치 완료!')
         

        elif type=="날짜":

           today = datetime.now()
           yestdate = today - timedelta(days=count)
           
           reset_date(conn_user, cursor_user, user_id, yestdate)
           conn_user.commit()
           conn_user.close()
           
           print(f'{user_id}님의 last_date를 {count}일 전으로 초기화 시켰습니다. 관리자님.')
           await ctx.send('패치 완료!')

           
    else :
        await ctx.send('관리자 권한이 없습니다.')




        

#-------------------------------------------------------------------생성


def get_random_success_message():
    success_messages = [
        "태초의 코인 제작자가 당신을 응원합니다!",
        "코인의 형태가 보입니다!",
        "행운이 함께합니다!",
        "코인이 떡상합니다!",
        "코인에서 빛이 납니다!",
        "황금망치로 두들겼습니다!",
        "코인 제작의 달인이 당신을 축복합니다!",
        "황금 고블린이 코인을 떨어트렸습니다!",
        "비둘기가 행운을 주고 갔습니다!",
        "코인이 화려한 색상으로 빛납니다!"
    ]
    return random.choice(success_messages)

def get_random_failure_message():
    failure_messages = [
        "코인에 금이 갔습니다.",
        "코인의 형태가 보입니다.",
        "비둘기가 코인에 침을 뱉고 갔습니다.",
        "코인제작에 필요한 재료가 부족합니다.",
        "코인이 하수구에 빠졌습니다.",
        "황금고블린이 코인을 훔쳐갔습니다!",
        "코인이 타버렸습니다..",
        "하마가 코인을 먹어 버렸습니다. ",
        "흔들린 망치질에 코인이 망가졌습니다.",
        "코인이 녹아버렸습니다!"
    ]
    return random.choice(failure_messages)


#-----------------------------------------------------------------------------------------------------------------coin 제작 횟수 초기화


def initialize_coin_creation_count(cursor_user, conn_user, user_id, new_count):
    
    cursor_user.execute('''UPDATE users SET coin_creation_count = ? WHERE user_id = ?''', (new_count, user_id))
    conn_user.commit()


#------------------------------------------------------------------------------------------------------------------공방입장 티켓 구매


async def create_cupon(ctx):


    print('------------------------------티')
    print(ctx.author.name)
    print(ctx.author.id)
    print('------------------------------켓 구매')
    
    conn_user, cursor_user = connect_to_database('user_database.db')
    
    user_id = ctx.author.id
    
    

    if await chekAuthentication(ctx, cursor_user, user_id):
        return

    count = 1
    increase_cupon(conn_user, cursor_user, user_id, count)



    cupon_count = await select_cupon(conn_user, cursor_user, user_id)


    conn_user.commit()
    
    await ctx.send(f"```운명코인 제작 공방 입장 티켓을 {count}장 획득하셨습니다!\n현재 보유 티켓 : {cupon_count}개```")
    



#---------------------------------------------------------------------------------------------------------------------


async def select_cupon(conn_user, cursor_user, user_id):
    cursor_user.execute('SELECT cupon_count FROM coins WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()
    
    # fetchone()이 None을 반환하는 경우 0으로 초기화
    cupon_count = result[0] if result else 0
    
    return cupon_count

#--------------------------------------------------------------------------------------------------------------------- 공방 입장횟수 초기화



async def use_cupon(ctx):

    conn_user, cursor_user = connect_to_database('user_database.db')
    
    user_id = ctx.author.id


        
    if(await chekAuthentication(ctx, cursor_user, user_id)):
       return

    print('------------------------------티')
    print(ctx.author.name)
    print(ctx.author.id)
    print('------------------------------켓 사용')
    
 

    amount = 1
    
    my_cupon_count = await select_cupon(conn_user, cursor_user, user_id)


    if(my_cupon_count<1):
        await ctx.send(f'```특별 공방 입장 티켓이 부족합니다.```')
        return
        
    else :
        initialize_coin_creation_count(cursor_user, conn_user, user_id, 1)

        await ctx.send(f'```{ctx.author.display_name}님이 특별 입장 티켓을 사용하여 코인 제작 공방소에 새로 입장할 수 있습니다! (3/3)```')
        await minus_cupon(conn_user, cursor_user, user_id, amount)
        conn_user.commit()



#--------------------------------------------------------------------------------------------------------------------- 티켓 감소
    

async def minus_cupon(conn_user, cursor_user, user_id, amount):
    cursor_user.execute('UPDATE coins SET cupon_count = cupon_count - ? WHERE user_id = ?', (amount, user_id))
    conn_user.commit()
    


#--------------------------------------------------------------------------------------------------------------------- 내 티켓

async def print_cupon_count(ctx) :
    conn_user, cursor_user = connect_to_database('user_database.db')
    
    user_id = ctx.author.id
    cupon_count = await select_cupon(conn_user, cursor_user, user_id)
 
    await ctx.send(f"```{ctx.author.display_name}님의 현재 보유 티켓은 {cupon_count}개 입니다!```")
#------------------------------------------------------------------------------------------------------------------코인 제작



async def create_coin(ctx):


    print('------------------------------코')
    print(ctx.author.name)
    print(ctx.author.id)
    print('------------------------------인 제작')
    
    
    conn_user, cursor_user = connect_to_database('user_database.db')
    
    user_id = ctx.author.id
    
    

    if await chekAuthentication(ctx, cursor_user, user_id):
        return



    cursor_user.execute('SELECT last_date FROM coins WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()

    last_date = datetime.strptime(result[0].split()[0], '%Y-%m-%d')
    today = datetime.now()
    
    day_difference = (today - last_date).days


    if day_difference >= 1:
        initialize_coin_creation_count(cursor_user, conn_user, user_id, 1)
        today = datetime.now()
        cursor_user.execute('''UPDATE coins SET last_date = ? WHERE user_id = ?''', (today, user_id))
        conn_user.commit()


    
    # 사용자의 코인 제작 횟수 정보 가져오기
    user_info = get_user_info(cursor_user, user_id)
    coin_creation_count = user_info[0]  # user_info에서 필요한 인덱스로 정수
    
    
    print(f'aaa={day_difference}----{today}----{last_date}')
    print (coin_creation_count)
        
    # 하루에 3번 이상 코인 제작 시도하면 실패
    if int(coin_creation_count) > 3:
        await ctx.send(f"{ctx.author.mention}님은 코인 제작 공방의 하루 입장 횟수를 모두 소진하셨습니다. (0/3)")
        return
 
       
    # 코인 제작 횟수 증가 및 기록
    update_coin_creation_count(cursor_user, conn_user, user_id)

    # 10% 확률로 코인 1 증가
    if random.randint(1, 10) == 1:

        if random.randint(1, 10) == 1:

            await ctx.send('완성된 직전의 코인을 용훈님이 발로 밟았습니다!')
            await asyncio.sleep(1)
            await ctx.send(failure_message)
            await asyncio.sleep(1)
            await ctx.send(f"{ctx.author.mention}님이 코인 제작에 실패했습니다.")    
        
        print(f'{ctx.author.name}님이 운명 코인 제작에 성공.')
        increase_coins(conn_user, cursor_user, user_id, 1)
        remaining_coins = get_remaining_coins(cursor_user, user_id)
        success_message = get_random_success_message()
        
        await asyncio.sleep(1)
        await ctx.send(success_message)
        await asyncio.sleep(1)
        await ctx.send(f"{ctx.author.mention}님이 코인 제작에 성공하였습니다!! 현재 코인: {remaining_coins}")

    else:
        failure_message = get_random_failure_message()
        await asyncio.sleep(1)
        await ctx.send(failure_message)
        await asyncio.sleep(1)
        await ctx.send(f"{ctx.author.mention}님이 코인 제작에 실패했습니다.")
    
    conn_user.commit()
    
#--------------------------------------------------------------------------------------------------------------------------------------------관리자 코인
@bot.command(name='관리자코인')
async def admin_coin(ctx) :
    if ctx.author.id == admin :
        conn_user, cursor_user = connect_to_database('user_database.db')
        increase_coins(conn_user, cursor_user, admin, 100)
        await create_cupon(ctx)
        print('관리자님에게 코인 100개를 충전했습니다.')
        await ctx.send('관리자님에게 코인 100개를 충전했습니다.')
        
    else :
        await ctx.send('관리자 권한이 없습니다.')



    
#--------------------------------------------------------------------------------------------------------------------------------------------출석체크






async def attend_date_update(conn_user, cursor_user, date, user_id) :
    
       #today = datetime.now().strftime('%Y-%m-%d')
       cursor_user.execute('UPDATE users SET last_attend_date = ? WHERE user_id = ?', (date.strftime('%Y-%m-%d'), user_id))
       conn_user.commit()


async def attend_fortune(ctx):
    
    user_id = ctx.author.id

    conn_user, cursor_user = connect_to_database('user_database.db')
    
    if(await chekAuthentication(ctx, cursor_user, user_id)):
       return
    
    count = 1
    cursor_user.execute('SELECT last_attend_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()

    last_attend_date = datetime.strptime(result[0], '%Y-%m-%d')


    
    today = datetime.now()
    
    day_difference = (today - last_attend_date).total_seconds() / (60 * 60 * 24)

    print(f'{day_difference}일 만에 출석체크함')
    
    if day_difference < 1:
        await ctx.send((f'```{ctx.author.display_name}님, 이미 출석체크를 하셨습니다.```'))
        print(f'{ctx.author.display_name}님, 또 출석체크함.')
        
    else :
       await ctx.send((f'```{ctx.author.display_name}님, 출석체크 완료!, 반갑습니다! \n출석보상 : 운명 티켓 1장 적립!```'))
       await create_cupon(ctx)
       await attend_date_update(conn_user, cursor_user, today, user_id)
       print(f'{ctx.author.display_name}님, 출석체크함.')

       
       return
    
    conn_user.commit()

    conn_user.close()



#------------------------------------------------------------------------------------------ 사용자의 코인 제작 횟수 정보 가져오기
def get_user_info(cursor_user, user_id):
    cursor_user.execute('SELECT coin_creation_count FROM users WHERE user_id = ?', (user_id,))
    return cursor_user.fetchone()

# 코인 제작 횟수 업데이트
def update_coin_creation_count(cursor_user, conn_user, user_id):
    
    cursor_user.execute('UPDATE users SET coin_creation_count = coin_creation_count+1 WHERE user_id = ?', ( user_id,))
    conn_user.commit()


    

#---------------------------------------------------------------------------------------------코인 제작한 마지막 날
    
def get_coins_late_date(cursor_user, user_id):
    
    cursor_user.execute('SELECT last_date  FROM coins WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()
    return result[0]

#---------------------------------------------------------------------------------------------------------------------------------운명들



def generate_fortune():
    fortunes = [
        "오늘은 운수 좋은 날입니다!",
        "주위의 사람들과 소통하면 좋은 일이 생길 것입니다.",
        "일을 조금 더 꼼꼼히 처리하는 것이 좋겠어요.",
        "건강에 유의하세요. 규칙적인 운동이 필요해 보입니다.",
        "새로운 도전을 해보는 것은 어떨까요?",
        "휴식이 필요한 날이네요. 마음의 여유를 가지세요.",
        "오늘은 좋은 날입니다!",
        "주위의 사람들과 소통하면 좋은 일이 생길 것입니다.",
        "일을 조금 더 꼼꼼히 처리하는 것이 좋겠어요.",
        "건강에 유의하세요. 규칙적인 운동이 필요해 보입니다.",
        "새로운 도전을 해보는 것은 어떨까요?",
        "휴식이 필요한 날이네요. 마음의 여유를 가지세요.",
        "긍정적인 생각으로 하루를 시작해보세요.",
        "남에게 친절하게 대하면 반듯이 좋은 일이 생길 거에요.",
        "문제에 직면했을 때는 한 걸음 물러나 생각해보세요.",
        "오랜만에 취미에 몰두하는 것도 좋은 방법일 거에요.",
        "가끔은 자신에게 작은 보상을 주는 것도 좋아요.",
        "도전적인 목표를 세우고 그에 도전해보세요.",
        "눈에 띄지 않는 작은 행동이 큰 변화를 가져올 수 있어요.",
        "주변의 소리에 귀 기울여보세요. 유용한 정보를 얻을 수 있을 거에요.",
        "지루한 일상에 새로운 활기를 불어넣는 것도 좋아요.",
        "가끔은 혼자만의 시간을 갖는 것도 필요해요.",
        "뜻하지 않은 일이 생겼을 때에도 긍정적으로 대처해보세요.",
        "주변의 도움을 받아보세요. 협력은 더 큰 성과를 가져올 거에요.",
        "맛있는 음식을 먹으면서 기분을 전환해보세요.",
        "효과적인 계획을 세우고 그에 따라 행동해보세요.",
        "주변의 작은 변화에 주의하세요. 작은 일이 큰 영향을 미칠 수 있어요.",
        "오랜 친구나 가족과 연락을 취해보세요. 그들의 소식을 듣는 것이 기분을 전환시킬 수 있어요.",
        "미뤄둔 일을 처리하는 것은 어떤가요? 지금이 시작하는 좋은 시간일지도 모릅니다.",
        "좋아하는 음악을 들으면서 스트레스를 해소해보세요.",
        "하루에 하나씩 감사의 마음을 표현해보세요. 작은 기쁨이 느껴질 거에요.",
        "책을 읽거나 영화를 보면서 자신만의 작은 세계에 빠져보세요.",
        "외출이나 산책을 통해 신선한 공기를 마시며 기분을 전환해보세요.",
        "새로운 취미나 활동을 시작하는 것은 어떨까요? 새로운 경험은 즐거움을 안겨줄 거에요.",
        "마음에 묻었던 질문이 있다면, 지금이 그에 대한 답을 찾는 좋은 기회일 수 있어요.",
        "일정을 조금 더 체계적으로 관리해보세요. 시간을 효율적으로 사용하는 것이 중요합니다.",
        "조심하세요. 오늘은 좋지 않은 날일 수 있습니다.",
        "주의하세요. 주변 상황을 더 면밀히 살피세요.",
        "오늘은 조금 더 조심해야 할 때입니다.",
        "긴장을 풀고 안전에 주의하세요.",
        
        "어떤 일이든 간에 미리 대비해두는 것이 좋겠어요.",
        "당신의 선택에 주의하세요. 올바른 결정이 필요한 순간일지도 모릅니다.",
        "주변의 환경에 조금 더 민감하게 반응하세요.",
        "자신의 감정을 잘 다스려야 하는 상황입니다.",
        "지나친 긴장은 오히려 상황을 악화시킬 수 있습니다.",
        "오늘은 다른 사람들과의 갈등을 피하려 노력하세요.",
        "당신이 이루고자 하는 일의 성과를 이룰 수 있어요! 오늘은 큰 도전을 이겨내는 날이 될 거예요.",
        "힘들더라도 포기하지 마세요. 어려움을 극복하면 더 강해질 겁니다.",
        "자신을 믿어주세요. 자신을 믿는 한 앞으로 나아갈 수 있습니다.",
        "오늘은 자신에게 의심하지 말고 동기부여를 해주세요. 성공은 믿음으로써 시작됩니다.",
        "당신의 노력과 열정이 결실을 맺을 것입니다. 오늘은 성과의 날이에요.",
        "어려운 시간을 겪고 있지만, 지금의 노력은 미래의 행복을 위한 준비일 뿐입니다.",
        "도전에 부딪힐 때마다 당신은 더 강해지고 있어요. 포기하지 마세요.",
        "자신을 믿고 나아가는 모습이 주변에서 인정받을 날이에요. 자신에게 자랑스러워하세요.",
        "오늘은 도전적인 순간이 찾아올 것입니다. 당당하게 마주하고 극복하세요.",
        "힘들 때 자신에게 '나는 할 수 있다'고 말해보세요. 자기 자신에게 힘을 주는 순간이에요.",
        "성공은 어려움을 이겨내는 데에서 시작됩니다. 당신은 극복의 주인공이 될 거에요.",
        "오늘은 자신에게 동기부여를 해주는 날이에요. 목표를 상기하고 다가오는 도전에 대비하세요.",
        "당신의 노력은 반드시 보상받을 날이 다가오고 있어요. 기다림이 언제나 보상받게 할 거에요.",
        "포기하지 않는 강인한 마음이 당신을 더 멋지게 만들어갈 것입니다.",
        "어려움에 부딪힐 때는 당황하지 마세요. 당신은 그 순간을 극복할 자신이 있습니다.",
        "자신의 목표에 집중하면 어려운 일도 극복할 힘을 얻을 수 있을 거에요.",
        "성공은 노력하고 참을성 있게 기다리는 사람에게 찾아옵니다. 지금까지의 노력에 감사하세요.",
        "당신이 이루고자 하는 일에 집중하면 성공은 더 가까워질 거에요. 오늘은 그에 집중하세요.",
        "매일 조금씩 노력하는 것이 큰 성과로 이어질 수 있어요. 오늘도 한 발짝 나아가보세요.",
        "당신은 이미 놀라운 성취를 이루고 있는 중입니다. 계속해서 나아가세요.",
        "어려운 상황일수록 당신의 강인한 의지가 빛을 발할 거에요. 지금의 어려움은 잠시일 뿐입니다.",
        "포기하지 않는 당신은 어떤 어려움에도 뒤처지지 않을 강인한 인물입니다.",
        "당신의 목표는 점점 더 가까워지고 있어요. 계속해서 나아가세요.",
        "당신의 자신감과 노력은 주변에서 인정받을 수 있을 만큼 큰 힘을 지니고 있어요.",
        "매일매일 조금씩 노력하면, 눈에 띄는 변화가 생길 거에요. 오늘도 한 발짝 나아가보세요.",
        "오늘은 스스로에게 박수를 보내는 날이에요. 당신의 노력에 고맙다는 인사를 해보세요.",
        "지금의 어려움은 당신이 더 강해지도록 도와주는 발판일 뿐입니다.",
        
        "당신의 노력과 인내는 반드시 보상받을 가치가 있어요. 계속해서 나아가세요.",
        "당신이 가진 열정과 끈기는 어떤 난관도 극복할 수 있을 만큼 강력합니다.",
        "오늘은 당신에게 동기부여를 주는 긍정적인 에너지가 넘치는 날이에요. 즐겁게 나아가세요!",
        "오늘은 새로운 아이디어가 떠오를 수 있는 날이에요. 주변을 둘러보며 영감을 받아보세요.",
        "당신의 미래는 밝고 희망찬 길로 펼쳐질 것입니다. 자신의 가능성을 믿어보세요.",
        "일상의 작은 변화가 큰 행운을 가져올 수 있어요. 주변에 미소를 전해보세요.",
        "좋은 음악을 들으면서 마음을 가다듬어보세요. 긍정적인 에너지가 흘러날 거에요.",
        "어려운 순간일수록 자신에게 격려의 말을 건네보세요. 당신은 강한 사람이에요.",
        "새로운 시작이 당신을 향해 다가오고 있어요. 기대감을 가지고 나아가보세요.",
        "지금은 어려움이 있지만, 그것이 당신의 성장을 이끌어낼 중요한 과정입니다.",
        "오늘은 당신의 업적이 주변에서 더 많이 인정받을 수 있는 날이에요.",
        "당신은 선택에 기로에 놓였을 때 무슨 선택을 해야할 지 알 것입니다.",
        "운명적인 만남은 삶의 모든 만남입니다. 운명에 가치를 부여해보세요.",
        "주위의 작은 것들에 감사하면서 하루를 시작해보세요. 작은 행복이 가득할 거에요.",
        "자신의 감정을 솔직하게 표현하는 것이 중요한 날이에요. 속마음을 나눠보세요.",
        "오늘은 예상치 못한 기회가 찾아올 수 있는 날이에요. 기회를 잡아보세요.",
        "지금은 고난의 시기이지만, 그것이 나중에는 더 큰 성취로 이어질 거에요.",
        "당신의 긍정적인 에너지가 주변을 밝게 만들어갈 거에요. 더 많은 사람들에게 전파하세요.",
        "최근의 노력이 어떻게든 결과로 이어질 것입니다. 참고 기다려보세요.",
        "오늘은 주변에 좋은 소식이 기다리고 있을 수 있어요. 기대해보세요.",
        "자신의 목표를 명확히 정하고 그에 맞춰 노력하는 것이 중요한 날이에요.",
        "오늘은 당신의 인내와 끈기가 더 큰 성과로 이어질 수 있는 날이에요.",
        "자신의 감정을 솔직하게 표현하는 것이 주변과의 소통을 높일 수 있어요.",
        "오늘은 주변의 도움을 받아 큰 도약을 이룰 수 있는 날이에요.",
        "마음가짐을 긍정적으로 유지하면 어떤 어려움도 극복할 수 있을 거에요.",
        "당신의 노력이 어떤 모습인지 주변에서 높이 평가하고 있어요. 자신에게 자부심을 느껴보세요.",
        "오늘은 자신의 가능성을 믿고 새로운 도전에 도전하는 것이 좋은 결과를 가져올 수 있어요.",
        "당신이 보낼 하루는 새로운 기회로 가득차 있을 것입니다. 눈을 크게 뜨고 기회를 찾아보세요.",
        "어떤 어려움이 닥쳐도 그것을 극복할 힘을 당신은 갖고 있어요. 자신을 믿어보세요.",
        "오늘은 주변에 있는 작은 기쁨을 느끼며, 그것에 감사하며 하루를 보내보세요.",

        "오늘은 금전적인 행운의 기운이 느껴집니다."

        
    ]
    
    fortune = random.choice(fortunes)
    print(f'Generated Fortune: {fortune}')
    
    return fortune




#-----------------------------------------------------------------------------------------------------------------------------------------------운명 출력



    
@bot.command(name='오늘의운명')
async def fortune_telling(ctx):
    user_id = ctx.author.id

    conn_user, cursor_user = connect_to_database('user_database.db')

    if(await chekAuthentication(ctx, cursor_user, user_id)):
       return

    cursor_user.execute('SELECT last_fortune_date, fortune_count, fortune FROM users WHERE user_id = ?', (user_id,))
    result = cursor_user.fetchone()
    
    last_fortune_date = datetime.strptime(result[0], '%Y-%m-%d')
    fortune_count = result[1]
    last_fortune = result[2]
    
    today = datetime.now()
    day_difference = (today - last_fortune_date).days



    
    if day_difference == 0:
        await ctx.send(f'```{ctx.author.display_name}님의 오늘의 운명\n---------------------------------------------------------------------\n{last_fortune}\t\t```')
        conn_user.commit()
        return

    # 새로운 운세 생성 및 출력
    new_fortune = generate_fortune()
    print(f'New Fortune: {new_fortune}')  # 디버깅 메시지 추가
    await ctx.send(f'```{ctx.author.display_name}님의 오늘의 운명\n---------------------------------------------------------------------\n{new_fortune}\t\t```')

    # 사용자의 운세 업데이트
    update_user_fortune(conn_user, cursor_user, user_id, new_fortune)
    
    conn_user.commit()

    conn_user.close()


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------명령어 


async def getCommandF(ctx): 
    messageK = '```' + '!운명 회원가입' + '\n' + '!운명 회원탈퇴'  + '\n' + '!운명 로그인'+ '\n' + '!운명 로그아웃' + '\n' + '!운명 출석체크'+'\n' + '!운명 또는 !오늘의운명' + '\n' +'!운명 바꾸기' +'\n' + '!운명 코인제작' +'\n' + '!운명 내코인' +'\n'+ '!운명 티켓사용' +'\n' + '!운명 내티켓' +'\n' + '```'
    await ctx.send(messageK)


async def adminCommandList(ctx):

    if ctx.author.id == admin :
        
        message = '```' + '!관리자코인' +'\n' + '!운명list' +'\n' + '!패치 적립 사용자ID 적립시킬코인갯수' +'\n' + '!패치 코인 사용자ID 초기화시킬 숫자' +'\n' + '!패치 날짜 사용지ID 되돌릴 날짜(last_date)'+ '```'
        await ctx.send(message)

        
    else :
        ctx.send('관리자 권한이 없습니다.')



    





    
bot.run(Token)
