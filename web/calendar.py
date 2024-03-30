import random
from base64 import b64decode
from datetime import datetime
from lzma import LZMADecompressor
from typing import List

from flask import g, request

accepted_range = [
  datetime(2020, 1, 1),
  datetime(2025, 1, 1),
]

class Calendar:
    datesep = ' '
    prefix = ''
    base_date = accepted_range[0].date()

    @classmethod
    def days_since_base(cls, time: datetime) -> int:
        return time.date().toordinal() - cls.base_date.toordinal()

    @classmethod
    def format_date(cls, time: datetime) -> str:
        raise NotImplementedError

    @staticmethod
    def format_time(time: datetime) -> str:
        return time.strftime('%H:%M:%S')

    @staticmethod
    def format_time_minutes(time: datetime) -> str:
        return time.strftime('%H:%M')

    @classmethod
    def format(cls, time: datetime) -> str:
        return f'{cls.format_date(time)}{cls.datesep}{cls.format_time(time)}'

    @classmethod
    def format_minutes(cls, time: datetime) -> str:
        return f'{cls.format_date(time)}{cls.datesep}{cls.format_time_minutes(time)}'

class CompressedCalendar(Calendar):
    data_str: str
    data: List[str]

    def __init_subclass__(cls) -> None:
        cls.data = LZMADecompressor().decompress(b64decode(cls.data_str)).decode().splitlines()
        return super().__init_subclass__()

    @classmethod
    def format_date(cls, time: datetime) -> str:
        days = cls.days_since_base(time)
        return cls.data[days]

class ChineseCalendar(CompressedCalendar):
    data_str = '/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4IoSBSddAHKt0i5Ga6ejT/F572/Oy3TL1olrHT3sZIewFZGle+uMHonknvFEjjLaiuqv068tu8SBNpQVqudndyKr3kGXgx3X8lVgG+57znxOchyk7cQIlV8RwSbPDbzKxvzR8cF7qy/Mo0l1ifjvNrZxlIzKCtnXzuxB9YH/M0/Uh6dEaodg4FlCXJ9InNu5r9pAyMDwLbbqYjBrtEUaMI0GDlP6YAcFL7UqaYmgFWAUTmBzEnacyQ9Juis4xJM3p1tjbvO7RnhkfytymrXUABoEgIIOdVU6OI2eBiUTlsmghtLW5exMpD8753W1V69b4ZmZ+UiP7rKLwrRM8rHLV23PmYTPOMQmS47iWnOEU0vsXs5ITC4n8fgUSw8h4jx5U5vkwLcyVrm/y78zTLtQuPfcHTtYG+IkSTf7ptJJAWTLl59v0ntW2xjCt1nXH5HrJj+H1g8c+Jm/EO/pHa+ypLYpjfaaXnebBR2dr2I9fZc21fxN2XvZ/pjDHLB4fMh9ChU/eiEPALs9MqJcQ0FdERYT3qD2CxfYwOUkyAde3gxWC4w9WG7toHifxV4upflqBS85FelzD2EVzxkrca0guUhlqRs3dFBrXjJllw3Vc4SrXz5DTMs6lAncGxy/OuvDZxx0EM2D8mnXVn/FhSBf6Vo05aAyaAm8fFggquV/CMFVK+9Mag4XTBvuNwXNU1oUHammSTyuhCbobr3y9raK6tCYO2O9X+BdUGSbXU/BGjKkReuU+bExA1iCNgnAESXazYpwzFxNTqkTWFAKCgrZUdzZqi1m9KfJY2m1VHO/hadri4b0SwOhqIvbwnvjJZg9PANNnNrmdv6B1IRgwgRvDVlihq1WY/09QF6DPK+QgwG27u1KwVZHF4sCcrKPd1wmFjRcYEYkZ4DYDoYKVBOl8MkYBz3L25Uz1Ym9z7K+MNMkIUJE/cWxN5RKcWrrP5jue0MF45h7Axd0EZ7qh9rOgvz2OT3ZVHJKETTmUJg+vqogMbE4hWsGq7vWDAApI3BEAGhwXukUYixu2bNkKTESbCftDFPQmgMCEIyCqslB1wUAzGrGBVWHsIrlEuzrwq9Yp89evDgPGAKVMp+76VOUfmf3rEV6AOSLX8d6Uts1bDN6tN1644rTRVRQdPGc1suwFxSufuHTxRs37eHhGb/VRh11YfY9q8ATOMLSSxqsku+jg6uZuJSUuLY2LLMQSpyDyrRHsoswrH8VK1NxX1ufNnSuGMBEHtaUikv1v3qbOlpHzGB0L9pkckfj0Nw2SKmoGKwmT1eFWActF7wj2vLYgGsMaufvqEfKL6ZlrGexkH/c+3arnhBL7wS+OvvTPvE0i01IcjQDzL0gJKPlV96RP/oyZATKIoW0a8DVFTk9x5locR7fnDNSOzZdIvcT2WzjPev1LpyVfxG6+s/ePbBaDkFIpexFpV9De17Lnw5CKoYvBsJbY+6dDiZd7EnxHoUwfxiVhH5OdY/05ibEu2wT0OlXXQERNpn1kb7LUDOvqbVEXkwvlwIgTFycYTB1KhngRH4257NpXqKaiMA+dlUXkbp3uSGltkbZOyJOS3G14QtA7gPnbf9rqv3v044l5alNWMfIhhixOnB17qFOSfGmFbXtCRcFHk3ICRHv1zi+ES9QE1Qa3rCeT+KBTtaQWeg4+ZfOmUP+hPPQEY2EIiZtFEC6PYSgEm4Lzno3bcOueN4XDpRXeAZvkEHeVFjDU8k17sgUzSyJbv1FZs2wENOHXGBi2jPS7jj/wt6tF2lPAAAfz5jW78pQwAABwwqTlAIAgpxAebHEZ/sCAAAAAARZWg=='
    datesep = ''

    @staticmethod
    def format_time_minutes(time: datetime) -> str:
        branches = '子丑寅卯辰巳午未申酉戌亥'
        branch = branches[((time.hour + 1) % 24) // 2]
        minutes = time.minute + ((time.hour + 1) % 2) * 60
        ticks = minutes // 15
        numbers_zh = '初 一 二 三 四 五 六 七 八 九 十 十一 十二 十三 十四'.split(' ')
        tick_zh = '初正'[ticks // 4] + numbers_zh[ticks % 4] + '刻'
        remaining = minutes % 15
        remaining_zh = '' if remaining == 0 else numbers_zh[remaining] + '分'
        if remaining == 0 and ticks == 0:
            tick_zh = '时'
        return f'{branch}{tick_zh}{remaining_zh}'

    @classmethod
    def format_time(cls, time: datetime) -> str:
        numbers_zh = ' 一 二 三 四 五 六 七 八 九 十 十一 十二 十三 十四 十五 十六 十七 十八 十九 二十 廿一 廿二 廿三 廿四 廿五 廿六 廿七 廿八 廿九 三十 三十一 三十二 三十三 三十四 三十五 三十六 三十七 三十八 三十九 四十 四十一 四十二 四十三 四十四 四十五 四十六 四十七 四十八 四十九 五十 五十一 五十二 五十三 五十四 五十五 五十六 五十七 五十八 五十九'.split(' ')
        second_zh = numbers_zh[time.second]
        if second_zh != '':
            second_zh += '秒'
        return f'{cls.format_time_minutes(time)}{second_zh}'

class IslamicCalendar(CompressedCalendar):
    data_str = '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'

class SchoolCalendar(CompressedCalendar):
    data_str = '/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4MifBB1dABkMAmyqON8WbAv99IB15V8ns1UNeCld10wUaGtxsvcpGVFl2tvdW0ffF0m1Eh3W7NzHJzNbURcWq6mgULfz6tcEdxmipnzFY7SyPu7bn8pX68DHc9CGtb6Ol3AJnSH6q+KYEiku14+3IDpCaXhqAKd6yC4yC59+GlYNuM232fASd/rwzlN1R+5RzKFWr18R7yrYpQmAT1qL9pD1Y58OjZxcRMEC3Q42oKUm/YEofnmzgxpnDwCcCnthwFaHVggq/XUijZrlyQUM1AlerK0wk6ZESZT4PMJp1lll5TD3pGUKjU4PD2P9jPy+IDA1SU2L6QnBQz2AA91wmnmyyB1fp11ftF+sKsCXyyei2sDQeG9xCTkjsmSry7RT+sveXhgpnNB16oYCJGZZ3zCPsfF5MnLbxjQPgO0pc5JoB4CjHb3MMNte0cQjp9l9XPFtmXZ2ByF19AlRccxhBybmDqcnThGMgKKscyXT9DHuOsWMvn9yUvoiD3Ired/N+OsVbEng0y1CXhEcXGnfToxeU5vPyptMEsNwUb2MsiOB5lTqZJo6++G6NYerxGePdPENAI0uKMypVFNK+V9vxrFe70yKZq2podp6uJ9jevMcgqRJJDDEjQf9JxQ6CrqOlwFLYKR8Rh6qVduMT4L9gOM8JrfylbjFCq18btqj7dHbyLgBJn/iaW8MM8DtBmFVPniKQlGG9H/DOITu9PRIih0SIvpRV0kPXe43JPeacoBT7s1FuMWBbab4PaS3EEzPWDvieCk6exwcq8g4ws/66I1UPPyHM3XWCnr82VG35Pk1/uC1OSYrZJvgUmbHP0zvukIoobAUIrKGcri3ZBuNfogYCWHFZcxdle28krJvKN3VQ2i3f8ATw9NU/uRFT1RQ2WIziF8t74ENnGDDXCm2zVFKMVViTg7KYY4ByPbjvJytAx47PP41o8E35dVE/8pzEucksvtVucCimee7TsPbPj7uwZiPe6Yn1r/kxndaX110eCkA2Pl0dfWkVl9O7UNMB/m/n8lrKb9ZhmUra7DJ53wjfQE/u5643/oKsnkw8A5sr+vgLojGyz5VsSjGN/H64AH5q2s2wQ2ciubuA3ysA4x/UPJ+iPW1zrhTlX7pcD9zPZHSNqvZ/SgrgVYcCmERWQolPiu7BKfiq2/pXCoa5Kssy/e8315U8eCYJrFBj9y9S0/kUcnLZWjpN7K2DBCUHejYa8aWTpbB8VKlQyFElSnDDYg2Jvsc1/ShFu6Q1lwngPGjs2Pc0DFBYMTpFw6ZDLlhwWsJ5jBGAHGW+5vaEo3ro+Phh+Xk9xGxH6vHBvmVTznKStVLcUPxgxwG5XKw9xwQ0wlQ9JH8fopJRIhcQAewRT02s+7yNQnzavU+p3wCN5pHH4gu+s/2mwuVwVwcnAwtCQAAAAAFK/DEtBXcgAABuQigkQMAoEV3VLHEZ/sCAAAAAARZWg=='

    @classmethod
    def format_date(cls, time: datetime) -> str:
        return super().format_date(time).replace('2023-2024-2 ', '')

class NumeralCalendar(Calendar):
    @staticmethod
    def tostr(time: datetime) -> str:
        raise NotImplementedError
    @classmethod
    def format(cls, time: datetime) -> str:
        if 'noprefix' in g:
            return cls.tostr(time)
        return cls.prefix + ' ' + cls.tostr(time)
    @classmethod
    def format_date(cls, time: datetime) -> str:
        return cls.format(time)
    @classmethod
    def format_minutes(cls, time: datetime) -> str:
        return cls.format(time)

class JulianCalendar(NumeralCalendar):
    prefix = 'Julian'
    @staticmethod
    def tostr(time: datetime) -> str:
        unix = time.timestamp()
        date = (unix + 43200) // 86400 + 2440587
        seconds = ((unix + 43200) % 86400) / 86400
        return '%06f' % (date + seconds)

class UnixCalendar(NumeralCalendar):
    prefix = 'Unix'
    @staticmethod
    def tostr(time: datetime) -> str:
        return '%d' % int(time.timestamp())

class UnixCalendarHexadecimal(NumeralCalendar):
    prefix = 'Unix'
    @staticmethod
    def tostr(time: datetime) -> str:
        return '0x%x' % int(time.timestamp())

class RepCalendar(Calendar):
    @staticmethod
    def format_date(time: datetime) -> str:
        # 危机纪元起点有 201X、2007、2000 三说，这里暂采用 2007 说
        year = time.year - 2006
        return f'危机纪元 {year} 年 {time.month} 月 {time.day} 日'

class SuzhouNumerals(Calendar):
    @staticmethod
    def replace(s: str) -> str:
        s1 = ''
        table = '〇〡〢〣〤〥〦〧〨〩'
        horizontal_table = 'x一二三'
        horizontal = False
        for c in s:
            if c.isdigit():
                n = int(c)
                if n in (1, 2, 3):
                    if horizontal:
                        s1 += horizontal_table[n]
                    else:
                        s1 += table[n]
                    horizontal = not horizontal
                else:
                    s1 += table[n]
                    horizontal = False
            else:
                s1 += c
                horizontal = False
        return s1

    @classmethod
    def format(cls, time: datetime) -> str:
        return cls.replace(f'{time.year}年{time.month}月{time.day}日{time.hour}时{time.minute}分{time.second}秒')
    @classmethod
    def format_minutes(cls, time: datetime) -> str:
        return cls.replace(f'{time.year}年{time.month}月{time.day}日{time.hour}时{time.minute}分')
    @classmethod
    def format_date(cls, time: datetime) -> str:
        return cls.replace(f'{time.year}年{time.month}月{time.day}日')

class GregorianCalendar(Calendar):
    @staticmethod
    def format_date(time: datetime) -> str:
        return time.strftime('%Y-%m-%d')

formats = [
    ChineseCalendar,
    IslamicCalendar,
    SchoolCalendar,
    JulianCalendar,
    UnixCalendar,
    UnixCalendarHexadecimal,
    RepCalendar,
    SuzhouNumerals,
]

def choose_format():
    fmt = request.cookies.get('acmoj-calendar')
    if fmt is None: return random.choice(formats)
    for f in formats + [GregorianCalendar]:
        if f.__name__ == fmt:
            g.noprefix = True
            return f
    return random.choice(formats)

def random_format_minutes(time: datetime) -> str:
    if time < accepted_range[0] or time > accepted_range[1]:
        return time.strftime('%Y-%m-%d %H:%M')
    return choose_format().format_minutes(time)

def random_format_date(time: datetime) -> str:
    if time < accepted_range[0] or time > accepted_range[1]:
        return time.strftime('%Y-%m-%d %H:%M')
    return choose_format().format_date(time)

def random_format(time: datetime) -> str:
    if time < accepted_range[0] or time > accepted_range[1]:
        return time.strftime('%Y-%m-%d %H:%M:%S')
    return choose_format().format(time)
