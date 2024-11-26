import yt_dlp
import asyncio
from async_timeout import timeout  # asyncio.timeout 대신 async_timeout 사용
import discord
from discord import app_commands
from discord.ext import commands
import re

class YTDLPSource:
    YTDLP_OPTIONS = {
        # 오디오 포맷 우선순위 설정
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        # 오디오 품질 설정
        'format_sort': [
            'acodec:opus',  # Opus 코덱 선호
            'asr:48000',    # 48kHz 샘플레이트 선호
            'abr:192',      # 192kbps 비트레이트 선호
        ],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '192'
        }],
        
        # 기본 설정
        'extractaudio': True,
        'audioformat': 'opus',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        
        # 추가 최적화 설정
        'buffersize': 32768,  # 버퍼 크기 증가
        'concurrent_fragments': 3,  # 동시 다운로드 세그먼트 수
    }

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict):
        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data
        self.source = source
        self.title = data.get('title', 'Unknown title')
        self.url = data.get('webpage_url', 'Unknown URL')
        self.duration = self.parse_duration(data.get('duration', 0))

    @staticmethod
    def parse_duration(duration):
        if duration == 0:
            return "LIVE"
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f'{hours}:{minutes:02d}:{seconds:02d}'
        return f'{minutes}:{seconds:02d}'

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        with yt_dlp.YoutubeDL(cls.YTDLP_OPTIONS) as ydl:
            try:
                if re.match(r'https?://(?:www\.)?.+', search):
                    data = await loop.run_in_executor(None, lambda: ydl.extract_info(search, download=False))
                else:
                    data = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch:{search}", download=False))
                    
                if 'entries' in data:
                    data = data['entries'][0]

                url = data['url']
                
                # FFmpeg 옵션 최적화
                ffmpeg_options = {
                    'before_options': (
                        # 재연결 설정
                        '-reconnect 1 '
                        '-reconnect_streamed 1 '
                        '-reconnect_delay_max 5 '
                        # 버퍼 설정
                        '-buffer_size 32768'
                    ),
                    'options': (
                        # 오디오 품질 설정
                        '-vn '  # 비디오 비활성화
                        '-acodec libopus '  # Opus 코덱 사용
                        '-ar 48000 '  # 48kHz 샘플레이트
                        '-ac 2 '  # 스테레오
                        '-b:a 192k '  # 192kbps 비트레이트
                        # 추가 최적화
                        '-application audio '  # 오디오 최적화 모드
                        '-frame_duration 20 '  # 20ms 프레임 길이
                        '-packet_loss 5 '  # 5% 패킷 손실 허용
                        '-compression_level 10'  # 최대 압축
                    )
                }

                return cls(ctx, discord.FFmpegPCMAudio(url, **ffmpeg_options), data=data)
                
            except Exception as e:
                raise e

class MusicPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.current = None
        self.volume = 0.5
        self.loop = False
        self._volume_cog = None  # 볼륨 조절을 위한 FFmpeg 필터 저장
        
        # 볼륨 조절을 위한 FFmpeg 필터 설정
        self._volume_cog = discord.PCMVolumeTransformer(
            original=self.current.source if self.current else None,
            volume=self.volume
        )
        
        ctx.bot.loop.create_task(self.player_loop())

    async def set_volume(self, volume: float):
        """볼륨 레벨 설정 (0.0 ~ 2.0)"""
        self.volume = max(0.0, min(2.0, volume))
        if self.current:
            self._volume_cog.volume = self.volume

    async def player_loop(self):
        while True:
            self.next.clear()
            
            try:
                async with timeout(180):  # 3 minutes
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.destroy()

            if not isinstance(source, YTDLPSource):
                continue

            # 볼륨 조절을 위한 PCMVolumeTransformer 적용
            source.source = discord.PCMVolumeTransformer(source.source, volume=self.volume)
            self.current = source

            self.guild.voice_client.play(
                source.source,
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set)
            )

            # 재생 정보 임베드
            embed = discord.Embed(
                title="Now Playing 🎵",
                description=f"[{source.title}]({source.url})",
                color=discord.Color.green()
            )
            embed.add_field(name="Duration", value=source.duration)
            embed.add_field(name="Quality", value="High Quality (192kbps)")
            embed.add_field(name="Requested by", value=source.requester.name)
            
            # 음질 정보 추가
            if hasattr(source.data, 'abr'):
                embed.add_field(name="Bitrate", value=f"{source.data['abr']}kbps")
            if hasattr(source.data, 'asr'):
                embed.add_field(name="Sample Rate", value=f"{source.data['asr']}Hz")
                
            await self.channel.send(embed=embed)

            await self.next.wait()

            # Cleanup
            try:
                source.source.cleanup()
            except Exception:
                pass

            self.current = None

            if self.loop:
                await self.queue.put(source)

    async def destroy(self):
        """Disconnect and cleanup the player."""
        try:
            await self.guild.voice_client.disconnect()
        except Exception:
            pass
        
        try:
            while True:
                self.queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

class YTMusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You need to be in a voice channel to use this command.")
                raise commands.CommandError("Author not connected to a voice channel.")
        
        return True

    @app_commands.command(name='ytplay', description='Play music using yt-dlp')
    async def play(self, interaction: discord.Interaction, *, search: str):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        
        try:
            await self.ensure_voice(ctx)
            
            player = self.players.get(ctx.guild.id)
            if not player:
                player = MusicPlayer(ctx)
                self.players[ctx.guild.id] = player

            source = await YTDLPSource.create_source(ctx, search, loop=self.bot.loop)
            await player.queue.put(source)
            
            embed = discord.Embed(
                title="Added to Queue",
                description=f"[{source.title}]({source.url})",
                color=discord.Color.blue()
            )
            embed.add_field(name="Duration", value=source.duration)
            embed.add_field(name="Requested by", value=ctx.author.name)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f'An error occurred: {str(e)}')

    @app_commands.command(name='ytskip', description='Skip the current song')
    async def skip(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await interaction.response.send_message("Nothing is playing right now.")
        
        ctx.voice_client.stop()
        await interaction.response.send_message("⏭ Skipped the song.")

    @app_commands.command(name='ytloop', description='Toggle loop mode')
    async def loop(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        
        player = self.players.get(ctx.guild.id)
        if not player:
            return await interaction.response.send_message("No music is playing.")
        
        player.loop = not player.loop
        await interaction.response.send_message(
            f"🔁 Loop mode is now {'enabled' if player.loop else 'disabled'}"
        )

    @app_commands.command(name='ytstop', description='Stop the music and clear the queue')
    async def stop(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        
        if ctx.voice_client:
            player = self.players.pop(ctx.guild.id, None)
            if player:
                await player.destroy()
            await ctx.voice_client.disconnect()
            await interaction.response.send_message("⏹ Stopped the music and disconnected.")
        else:
            await interaction.response.send_message("Not connected to a voice channel.")

    @app_commands.command(name='ytvolume', description='Change the volume (0-100)')
    async def volume(self, interaction: discord.Interaction, volume: int):
        ctx = await commands.Context.from_interaction(interaction)
        
        if not 0 <= volume <= 100:
            return await interaction.response.send_message("Volume must be between 0 and 100")
        
        player = self.players.get(ctx.guild.id)
        if not player:
            return await interaction.response.send_message("No music is playing.")
        
        player.volume = volume / 100
        await interaction.response.send_message(f"🔊 Volume set to {volume}%")

async def setup(bot):
    await bot.add_cog(YTMusicCommands(bot))