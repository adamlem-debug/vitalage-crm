import base64
import json
import zlib

import frappe

from crm.fcrm.doctype.crm_view_settings.crm_view_settings import (
	get_route_name,
	remove_duplicates,
	sync_default_columns,
	sync_default_rows,
)

CONFIG_PAYLOAD_B64 = "eNrtfU1bJEdz4F9JIa8H9EIPjDTzSkjofRhoZvDLAKIZjbQDT6u6q6Br6K5qVVXDIJnn8XEvPq0v++zB67354NtevRfZf8S/YH/CRkRmVuVndTU0jGzP6GOgMjMyMjIyMiIyMvLXhf4kL9JRN0z7xfU4yhfW3/66kASjaGF9YevoFdsKsogdDoOE7RbRaGF5IRgO06tuFvE6a8sLozScDLH6DtSHCnFeBL0hL4vzPE7O8ZfV5YUojKmke57FIRXzvunHPM2K7lkcDaFkoZ9FQRGnyYL4nmZhlMH37XZnC74JXPFD2j/Gn5YXqCnHfhj0oiEUqiWificaRv1CfhTDjGFg3YJXzqKfOWrpGBHIsc1kPB5Goygp8pPkFQyiT7idJFuDqH+xMhnD54NiAAguLwziMIwSGm2cdIdAiu5lHF1xWiRdoEwSBlkIAx0WOKI17DEIu2kyvKZW4ygbDaNLxH/VGOgOEedmuRpgpwiygm0HhTlM9ZMYZI51uyEvKEf5sPi2k7AhtlESfmBcD64SmlEV0b04uTAQzaJ8DGwSI1tPcmrhYKHX+b1wR5T3s5g6qfqYMqz91CJ/ZwRLmh1H7811kaTKBKw+9AQcRaM4gWXPOrDy2E6asebsk4m23Rzads/SrGsxlDIeHc+1JnieIqaisx0uJocRjh5+SPrRcEgigsECLSb5nIUmh9WbDC+6WPgQgjTIL6qxTJWnBVRHbuDVHcvhedC/GKbnJ8lxGqYnyW7CDrP0HJYSSNLtNIlAtBIVo/BhRKp/NmnkgjD/Aeaw6Y5IM+jfETdDWF4w2kxuhPB5MizEb/uTIouJ/fvad6jVj6PsHKa3E4xgS4XyIXZOpcewgQbj65Ok/R6mMQmGbAwbFshgqAUjjhMBhXZaA3KnP4hwKhhgVcTQ1FOc290CUkXQLxgs2CgD7ovzfnoZZdesD1METYENWK4qAPRlnKW9OC3iPn6gTXjrxauH59Xvga2Gm+cRQ57tREUBLDebtFlVOfWD8OWLNIXOqxW3mxTReSYB65xKc8aeQ7/mNnxOULp9AaUba1BcO9gddiZbOphi8Zioq6NY4lYurlxFrVpdfgk0Z/QdW9VsI+krAITAbzYo9yY5n+GV8qPsDTSJ9BI+NN/BIgGjYqiMwzC3NW2M1E8UsrMsHZW9321cp7wSrlHqAxZOltJK7lznYLawV0ESnJPipwPDjmjJXoEs5mub1iv/MYRBix/zARh4XOvJYNXQT9EoiIe8oorTIfSAAuhUyoSusp6lycjl6Uqcd3vxcAiSpdvnn0jsdHNCu3segWQHbDiOYVG1hGpyJndz9pzDYFWhZrg5O0lAES66wRlJWKwDAxsF2bVSR2UAsuLUCdXnSJk833RtETFYxYqK+bwdBcOVKBsnwFJdTjWarXpSiIYKLbZEU9jiWPvocN/W1l2d6KQY4sCotqVAB/dLAMEu4+Aad9FuHp8nNDrfaA95RdaRFTXx4wHmXNXV6vx/f//3/5sB4JyBzDmOR6CGwKf/xd4ERX+AP//d/2FHcX7xIJQYRaNelOWDeNzVDHMfQV6V9Zlt9Ot08YE2mSEF5QQtvNxtTs1Egyd3pIFinTWggGkHesevgDVGP4VWH4QecXKZxv2oC8J+QpaPjxS7vCLblRUdVLCATSWAQqw7i8c7jX8cxE1Gf8ir1YxdAHKP3CLQhxm0aql0c2Go1A1ftbVYR2ngIIQXeD1JxgplH26TFEgk0nqsocG+UscxbBWEe6RewnyYMSurUBjdDaSgalJ5JaAA56ZCYpLRv3luniTPwVgGA/lBCAJ6TBZos5RPEwttbMLU1ZHXiIiaDqYKysJ2ouwM0wAJFkZnAQCEL6sPQid9AHHSH07CxtIjB1u7bDBFemjA3RSqIamLVC7irN0jccA0bU6Y13kzogig04WMRr/fAzkytPESsJwa0+RIaTGVMCr4JtSZ5B+WMtwx2XAF8crTV48NtAkpMpPOH5Ae0xeNoEXtgtGBeWlgk+tDD7/hIhE0mL5AHGCnUeP3sTCajH/KqBuM1cf5D6eIlXuYwKipziE4oIG+oQOeQpHfiZZR6ondfBz14wDPNZpo56yjVq9T1HXAU/QLnYSO83nr3H06iZqe1tx5RQUZYD4M6qybMuLGs6IUEFP0ep2sLrd+RSpnrM8D2L/DmI7oJ8OhdE166UJV2Q5UZfuKF9Mgjw3Qs8oUOjb0hq5pMQO34YU9AKZIV+GOLkeMxbpsdXi9rebG+Lj3fsrKqEDfYnHcdeR5Osn6UTeMCo6pb/wdqgd8UCgj0qlggjJowYsf0t+tjlMN0PGPclur5RijDsbNzSYdtMXODwvuf7z9dDQOkuuuvmlaTE2V2O62j68VIDM4rR9mSovgff3wjoP33qGVjX37vjLyDzK6vMiiCPBKQthE0OFRtzipLoO6bF/WdS1QB0j38EvqfJCh9+Piuo5rebGLX3mJZ1k6Rv9BhjeGlYPn2WkY1YzykGoxUct16KaB8bCxQqoHn8V0khRZ7USWNZyyRxa6h6YPf8oGW2JSqutbv0T9QfxAlBgESRLV7a5bZQ0XJcpCn6zSyOj3HO8mDIaSY6zV4YBi+zop6qRsFIVxcJK8iXp5PPsJW2OaYPxMJbyrsLaSKlhBk9/5BSu8vnUVxDSf+ccoOXeUXBlReG8TLYwAqQn75lpYFO2RV700ABlrIbQ1N13gVcwg+7gfs0Idezgp4958496e6AF2hrpZlXrWvk6UKcvg89WT5IunJ8kz+Psr+G/tyerD8IAM3QIYSVHHBTJOrC0qOo1uA5ibMuHEblobQ6yp/lzA0EuSZAJgaVa1rLvcviCInU2tQHHGDwo5PGZuBWT38qaXp2bw4XiDPGSQynzFXFfFqry3i/qnWenWXQWZVGCtlbadwRTOVbA4eA6j2HPSxiaLqrol79nGIIrfuOiW7t7sfZgniuMN8xSqFtcd/OogMbO6D70067kUZD1BzIGsITZTbMyRLiK/IXCruyxdD3IrtBQN4CVWOh8dBkMJ5H0cQhDrBzKoWhDodAwbJfbCbSaCWhwGa7jSbRSUcWHPyeMPoDKN0UVu6ITHbY+PrUjc2y7tB7l0NZmHtNZnKFZDF9XiF/mMJQKpD4MAd8cgfTQ334Mw2DeQyghPtAIaE0IXZ+vxhmWRDUGBVUDmIlyKWkkznvCLz872pxwPID/rljrsKas47cn7nDOk4VldrKQZudBEv/Cw3SKoMe/wggw4hekchzldkVRCUNh8yIa819BmZ2Mkm4Prw5043eBqMWjufnPIYykm+KtP1HGlV/R5t35eMS/o1Yb9OIhWLn8Q/R+DFWjsEsQaGQKROV3DYmL8fvAaN8fpvkkiygKT7SAL1GofuCyM6+oIb9ov/FfKN6XewSVBvhVjJB8hg7crvIwUkAgywhUjRhjxzTJ/gT5HDUqcFfc9hMzlnbTM1Aqx8P0OpIT+y7tdYu4GLqwfN+7PuOfgbdhQ00zMSH9SYY7dDk9aMvi8WJJRV1Q829xEsKgJAhusuqDyGEmC4XFKhkpaBVov+q4vhtJdHDn4j+OwDwaRt0kFX2SeUw/nkd4e7Hkt3CiTbn84uLTfr/3ThAlLeQ60lCZhL2f5RopukqtfBhUfcAv1Vd508cBbXx2+XNVUV1P/XQ0miRCLdRKxJ3ZyM0rZWnv2tHfYHz5TiV/WbuIJeHVgjBCrclFqNHV5bnoMOVXCCSo3L3+w0yZZke3GprR5S/vrOoqMsP0XCE2Eacr+BRvRoo60NRevykBDPIKlHSKS/b3xzb7asjgX61cD5F1FuEhrFbgjqzUqpTHkz5kcKvQynyhZd6eq3CrmioYWlFTXEYjmHWMOBVPsQu6GefgLncPXTn1dlNTOezV4cpzTv2rcUx6snB6O9Xh1laAU3loaAbcBs9BekUjhYnrng9hDx92eW93R7oO9D0pmrQpCmTvir8Oa4rGVnNuP9MouMybrwFWXs67leH1ZJYxkKt9XsakcMx/aGOSxnQ3Q8w1kgc0xGgEd7RoxBDuYNEI5bHa3u+gOKbjfORWxSs9Ug8IceqWQotQICmWjm09aYq5oV3rirKhoGsmhSMyQStR3Od19p6uiE3i95deO3AUhyGOuqSSpkhX+rVG4rCXX9rmoNMccRoOo+C8ss4ugTXkxj+b5n5+fjWYornHEtF5aO5nZ8n4ITX38VU0mIvm/j4Z/zKD5n4RX7iIeX0e5jMo9EX/596dFfr8GtS4RKl3FvSjXppedGlJlpqd5qx4P5oYlc/SbFRWvpuRUIWcaJ95KIa+jM1IBh1O6Q2xT8qNDuncWP/Gz5pnVEErWX8XFdSW9vNWQelMKsjRrwXsUqS32lfFkZWuIVQw739npVGEE+6cmtsQJMAHwv+OmoEYwd19nWUQgZD31f45zuI0K9eSabdrZ09Ve+tIyiFG+j9PxLagsI3DCTpR3Y+6IO39MgilNmFs3I6DYX2nF+eihmGqnqnOuPppPoUNIQNs5sCQLguiAm9OsAislBOM2axuO4Z5rSjXAOa9nvgZ8x0WkzyCvsNK0hTafNJ7F0nNl7gJmKuIzkudlX9T/ErpMM3k4hmDitQtBnEuGZHvl32f4vSFsjjzcv8HVq5+UZdUrqigAZAyCUvPTwDGcxhcV8pB9youBl0jmZGoG4bdyziMUtTz+Xov4eS97uqqUHhdba3sSHJr97bjpCgritIRagCgcV0IYQXGP8gRTHfjxlmXH2ufaxSvtEY+AfHQfaatPZP2TFJSqphEefnLVRQmyq/FYJJVv51lcUVfmJKs+m1SwdPR/NIj4zDQKu7HoC6pGj2nk1om+AeolPtsmHfDn8Naia4rzu8urmoFvQ78Z7BZFBykNaOEaKhogTonkyU6auryWo0CmUFcVyEZdxAZaujGHcSGdpaUFOVyn3FnrQJEptLhdBmonF1iLkriJy2e4jCFNQSSivm9arxVV0+lxqoAIgNv3TvGufMMNoAJHohhUOJQ9U7xaKb1hecR2BQR6wSXRPY4x+tBPGCH94/bYNpvedBkG0AU+Cc7SfA/gMWEMwLTFVFDcUq5juUM/sRnskqrytBUluKf+v5k4+obdCqRkCB6IlMcnvyB3BrFBbc/Ftafah9hAYF4gZn58tkXq1p0TIemjnU4ERSmpuBOhrm4GFeoKF8RmIVFFvdlVryZp07cV7vrtK0p0/Yp27jDH6Tmp2zrYH9n98Xro83j3YN9+sS/b0fD6BxTVzFMfctGPBdZDj9cC6owDFlixSDKIwwHPYuHUd7ijcvkhZyUr8CsxvRWOQujYdyjlFjQNHrPT1lYniIYjDhNQERxEDyjGQvgw4D6JxBBFXcLPAH/ApaXWA8qjfJoeFmicFfK4H/b7b32i83j9nb31eb+5ov2UffoYK9NK6IcIU6rzNRWLZPNvb2DN9AO63cPjw52dvfaHWj4VrKwAuF5FiT9AScVyCBHjTLIzF3supTpq5nlkbvoJUiVYsC2ZKgx6VBY71SOidP1mOYbLxMCyWmR5ExGObAiZT1gBiH5QtYj/mDBGPjjMgo5hCNcWIeSYdjrccgnENgDMWdXgyiJcGViU8lYjPtbWipxNzud3Rf7gsr/TqnL63UCHGLJRVYJMplrOng0REHZqbt8LjbYWQb0jlrnoM/Rp0UJTRTkEWUcbGEjLFqS0Kq8dfoy22B1IGClAZ6baotKUpPg1tMZnizgxmFjbqISSgHUFbJHxcOzMqcDFsItxSDMUqSzTVOsnEfJJE5A/Gqoc9kC2xs29lELL0250F+X3SP+qnytRCvsiIyzPiZoJf4XB78s6NPuxjEQmyzuorQ9wrDfWlOAyswL0KbR+tY2XzGHxSBLrxbVAs5xP6YTWt44RspPWYiVPUrD+OyaL1Q+ctoaWvq+rFFaDJVTm/LPstAeN8Cm8UbvAXs0fMqWOvmdRFg09QpS5ZRvOB9iyGGvRX3kjmG/DHKSTMrqk39+NT/wFmAYkI65Xna7XFeRa5Tr8Luymu3KGeGw7lg2VoObZYvw9MM8Zzsw5mD6bH8PEpIkek4xjABNF/iypizuliIeBPipCgt1TcBa6pkg0BY5fcomJwtLuFrfnmqLC/+IGlKlBDCO9tDcbAccpTZdNylmYd1C8ibhotrKogqORMMIhmRBWp+CC5c6CXPqFhaitfNezb2pzsmtulLh9AmvWhuzatVysIbWhNgONIcAj1pgXMBzYKrGl3E4AXnHN7PeddV4hwYE+gXpxSgbgSkmpJqjQAI9OWxVzIflEngFg3R6UjJgtV9Fw+EyUJg0bozRB4Eku2ZR3g94DmObYeVG25Bba7iUmNHJom7WLOv7+ZJ6lExZ1ndyZNW7yo4EYL2uc5MRdT3sNpx4LFRJD7P9oerbXQw6BbcdUP2UTnDUPgNlv/ExMikx2h7u4ub7MTWrrBwy8SmTb2PklpUpb/FVt5lsY3IrI/O0D3/RWWKAduJT9ox9hv/47cxdugnjdRDcj6U5FyNt6+Xu3nZ3+2Dr+MdDbpvZ6U4qw+xw86i9f2xVR58KryQqHG8+B+m6s9ve26ZKdsCdhIhwlIrlg0O8Rud48wi6A1VVqaOe/WCl9v62WaUK2sQK+wdaIV0mWqjU2S2yjbhmBgv1Op1kjN64YdzZyAYg7mApxGfklihYeSOKhNvBm31QoCvw5rs3alcv6XYS51SCghmXbYIT3A4ScudAB+17vKXqRFiJ8omYIsZQEFzMVRfobGkpzgqUHzA/GaxycggKXXqE6Z9pK+D3KZi4twU7Q9AvhtcE4qj9and/Gwiwvfljp/v8x65gjF8VI0y5/gqq2dofFQNNeTQKi1aVouoNKSh58iWV3OijpFvjjO6r5ahN40bI9y48Z2uV/LW3+by916nF6mRhOx0P//W/XVwzFGOX15odqaPJf78I+rq5qiF8svDnNClA8EpABupzEAivj3CtMWT9+cmDIg1BpynN4EkRD3PcWJHJTDuWF1KLxSWHnXj3Me4Ab7FXm8cgpfZfsC0QLuxwb3OfHR286SgM3A6ADXT+pkUbFzlLrxIm1w3DUczRw0UrhMJs0itdpVGcvWfx+STDQ2XECvjTuWI0jQHomXeFprbhrs91HWWXNToqrRkVLshNdGtImTFtlq2ZxoM2xM1SQ4gFLANLGYbH1DLVKtpaBS0roxNxButX61XbtjTo/GJnvvGrba3plqS+ly37qpOYVuorW5vVptrM1s0Jserqu9a6OTla/RtjhBh/s/HWxlicw/iG4iiqMLaKzL13ygis4mrXtYqULdPuVtv2tOLTZS/n4FqT3EObgOQkSxX/lHUKaQJVc1SJCHwfJ8M3UWAfHqdZkMXDa7099gWbDXlaKVNEkU36ZALpW0+5OgQub5UNXFkbJwunwO7qBwNjTcpI28RagqITr3thHuIY5mabHey3S5nEDuE/t3yen5RVTEONFNrUZuKigWYK8vVQyhu6dWhVkmtDE5WlHqpUrdbKknmkVqmkSn1zAZV4KAJY1tXXUlkTVVWlVrWkNAxKGhiap9JSWXFLlUUulEgTb20FLuk92PyrElNhPh+zl0sYR7Bqezk6F/EY1XBSx3Har1D7HuIt/2t06PSjHBU9ZArc3oXDumovLUGvl1MbtunqLPVptwtU3yg1SEtqkw3P1irBe7yNeHQbY/i0myq0M2IcTDrB7GKVqU4R6+qAhXte44aGPd1ltXIIL9rHXMKz9qvN3b35gJZQ6GBCWCmmkkCfDSZ0eItNwmiFjl1VBu05ShIy9p1lyv0xzyZGvJV3wbIoNtb8W5uYTmXgjWbSbibkXYl0M97Lon48roIXgegOkJxCS47+jeYPyoRbe7toIG1tdtpsdx8k2qvSeTI/hqyusjdhyBqls9ydpvGjcSmlvsJcWJBQowAh1FQknsZsK4Rw+T+VYsE1+jiWLM+n3ava3OmM1EF6feryQzScipig39yxE3Cnuv1JryMPh3qAW6ru3LNBfZYqi7YT0TYpfWo12vMIAzDDrqbImPoFEKsq14/J3ADEauClXcu41DWn2oOxqgPbevWBN/dyN1tPMouySggAlC5q9ERv+WMoftzPRisI4LE+iX/Q14fnKOfu8o22VnQKH4M8ma9EEzHDJlVgLx2nv6RZ8i//M/ntn9bZOB2m//p/LwI2Hv72D8mEjX/7x3/524hdpMm//O1v/8R+CZhJGTCUFl1KoUVgFkIP7N/+5r8zJ3F5qKKPuiNQEIPzyEb/m/G322kv++2fAUqy/M3j8bc6dKrhGdWEXVCkXX7x2z8OUjb+1//x2z+Ng3DCLBAwyDQ5/3Y64nKw3zwWTeZHupZncD5kj6/H6xUaZt+VCLJQ72UKTJfm4hIM1u7gmTGlyPz8BwX5wxSI9g9F9C9/i0wDHUxG3sHwti6knD1ow5uF2RxoqyhvI5JsQvMd4WLyE98WfFMUxbmRFwZfkfiX5Ld/GF0EUwhLJytzJJfFxX9gj4CNvwnYIIvONk4WHjkWGYhso8nJwrcHRXSJa7ao1vE/l6v4m8fBt9jXo3uV2OQ8uQeLqAwqS0LUsBd1U0do3w53oaGZ12iIYkPYEH8vO6ZuQ/y9XEPCV0F2wd1u3GavDm3Bwi8t+5YxLlClc6cq7XcBS1+Q9rHGr+j0uU4osLJLgTxxFG7sBMPcM7wKU7wfHBeL93XcLY5a2QrrXCd9npvSyNT6IEHxm5jxsT4m/nd85L3d3tzr0kJUT4y5CUtHhpudP3e57WhVc17nK8+yseFRe6cNNt5WW7Kmdn5r3aVwtNvffOVtVFkN8/Trvj5E3yNGpDDEpcP2dvf/3N5mxwfs+OVuRzWk5zcNKg3RhBJRP+bsWJ5OvLuDhyrA/PXnRCflVUDF/nUeD9VN3LoW47Bc06yaN0dM442CgX18Yx3dcAG8ZB4nKmNHd7hKinXHnuCVnU7S4B8Fou5DtwdurxCtjjq9swjW+xGdRxFItXzAqlxaFFBbZeadW6zQ6n/cWKFX7VfP20edl7uHXX62YclFT2Y1ozEedtQ1dQe1zCcy4TrCmzAOSNbhtn6ovbK2fI8RDiVtOvzYFU/Tjg+2N3+c3+TRfFCKDZ2OXsFpCDyn4HRzxLpBO4fsE2Ll9IGIevxy8xjPq2FP+7HdOW4fSdJWAVCVOGA8C13Ogn4RX0YYokUHu6CtkuMpLvJoeIbHQrx1D8QRqL/slyhLZeWzFMP18UwYCDHHiJOIMqs4mHhe01iuzXVW9vLhJvL5a9Dx2ev93e9et0Ep6RzPj5Klm04P3FEOm/UVs255DuuOm02/ONXFg8TqNxEGXOGx7jwNKE/8yy+WViDwNXjjd4rwXOIQNr9vM1QU1SAwMEcoBiOLz/FezDr/utZim9XKFluwjHPnVZ60GD1JA7s92MTBsD8ZarXRzplvNENFU5ue6ozp19FAn3AocQ691D5JWjIhtzDiX4MWnycpRufiLRa6npZvHGeT6Pdi8KpPxCiy+oGvgUvGeWDtTYtTFveG41zdsgrEhUckjYP+RXCu3/mcD+vCFn/8uqNHYlMyjw+vIALNtnbbRy/a0BYD9BztlSyystWL9n77CMzN3f2tvdfbnkbO1Ll6n7XtraS4ujRUpBMGaXNvzlaQY0g2UtcI1Ibv4rAZliAwAnHD1SCG2adt6lEulJQcZEsehxToxlsrtg+s8jgNlxlHigLE04LHetO0yFgYgqWhUD3pq3Af8mIY0jVf+HqNB/vyN0BQ3Eg3CAJqE/YrohFaCn/hxZgtYn4jZPtVmmC2RUrusq7fK6R8hlGGonAdZP7qsl6ozP06yPtVh0YD4OmO3kjcSvSDf1YP/pkFfu6h39vtnc3Xe8esotT8FrkYaMmvMAWrLYrTsnm5Kpvn6I7am9ta7Mb3m3uv2525mkKwsBSfkyrYLH+TKbKUdnKa3XJP04h16VUPoxR/GoSK/GLNAJBemlb6voTokYW6Hfz7ivPfboNN9mp3v83evGwfv8Sg0pIcDB2Q/K7D3"

SAFE_FCRM_SETTINGS = {
	"enable_forecasting": 0,
	"enable_sales_hierarchy": 0,
	"auto_update_expected_deal_value": 1,
	"update_timestamp_on_new_communication": 1,
	"auto_mark_replied_on_response": 0,
	"auto_reopen_on_new_communication": 0,
	"currency": "CZK",
	"service_provider": "frankfurter.app",
	"brand_name": "Vital Age Clinic",
}

DEFAULT_VIEWS = (
	{
		"doctype": "CRM Lead",
		"type": "group_by",
		"label": "Group By",
		"route_name": "Leads",
		"filters": {},
		"group_by_field": "status",
		"column_field": "status",
		"load_default_columns": 1,
		"is_default": 1,
	},
	{
		"doctype": "CRM Deal",
		"type": "group_by",
		"label": "Group By",
		"route_name": "Deals",
		"filters": {},
		"group_by_field": "owner",
		"column_field": "status",
		"load_default_columns": 1,
		"is_default": 1,
	},
	{
		"doctype": "CRM Task",
		"type": "calendar",
		"label": "Calendar",
		"route_name": "Tasks",
		"filters": {},
		"group_by_field": "owner",
		"column_field": "status",
		"load_default_columns": 1,
		"is_default": 1,
	},
)


def apply_vitalage_site_config():
	"""Bootstrap VitalAge database configuration without business data or secrets."""
	payload = _load_payload()
	_install_missing_records(payload)
	_apply_additional_property_setters()
	_apply_custom_docperms()
	_apply_vitalage_crm_settings(payload)
	_apply_safe_fcrm_settings()
	_apply_safe_crm_settings()
	_apply_safe_erpnext_crm_settings()
	_apply_notifications()
	_ensure_administrator_default_views()
	frappe.clear_cache()


def _load_payload():
	raw = zlib.decompress(base64.b64decode(_pad_base64(CONFIG_PAYLOAD_B64)))
	return json.loads(raw.decode("utf-8"))


def _install_missing_records(payload):
	ordered_groups = (
		"custom_doctypes",
		"custom_fields",
		"property_setters",
		"crm_fields_layout",
		"crm_form_scripts",
		"server_scripts",
	)

	for group in ordered_groups:
		for data in payload.get(group, []):
			doctype = data.get("doctype")
			name = data.get("name")
			if not doctype or not name:
				continue
			if frappe.db.exists(doctype, name):
				continue
			frappe.get_doc(data).insert(ignore_permissions=True)


def _apply_vitalage_crm_settings(payload):
	if not frappe.db.exists("DocType", "VitalAge CRM Settings"):
		return

	data = (payload.get("vitalage_crm_settings") or [{}])[0]
	settings = frappe.get_single("VitalAge CRM Settings")
	settings.external_calendar_removal_status = data.get("external_calendar_removal_status")

	settings.set("calendar_task_types", [])
	for row in data.get("calendar_task_types", []):
		settings.append("calendar_task_types", {"task_type": row.get("task_type")})

	settings.set("calendar_cancellation_statuses", [])
	for row in data.get("calendar_cancellation_statuses", []):
		settings.append(
			"calendar_cancellation_statuses",
			{"task_status": row.get("task_status")},
		)

	settings.save(ignore_permissions=True)


def _apply_safe_fcrm_settings():
	if not frappe.db.exists("DocType", "FCRM Settings"):
		return

	settings = frappe.get_single("FCRM Settings")
	changed = False

	for fieldname, value in SAFE_FCRM_SETTINGS.items():
		if not settings.meta.has_field(fieldname):
			continue
		if settings.get(fieldname) != value:
			settings.set(fieldname, value)
			changed = True

	# Intentionally do not touch access_key or any other credential-bearing field.
	if changed:
		settings.save(ignore_permissions=True)


CUSTOM_DOCPERM_B64 = "eNrtmlFv0zAQx79Klec+xHvsW8XEE4FqG7wghI7k1lpz7Mp2GQXx3XGSKrAuW5fUmewcb5bjuP71f7672Pf5V7IFjdImi+TNVTa7RBDJPNFKoOu5BoFmloGENWrXzW+/qnvpmot0nmxRlwK/o0gWbJ4YFJjb+oFGKOq+e80t1q3c9VVN97RwAw9Ns/tW8uadHGRezeSaUKIs6lYJ5u4w41bpZiD+aJpuUl62vWbjIJpVaS4PI0vgzYxuIGqjZLOE3/MXMH80zwJfPAucBg78Qa9B8p9guZI9wdOXKs3+grMB4OwEOGvBWQvOzgI/beWU2ePe4U+w743FcvLCD3PpF9EKfuVAZyutbrkD7i/2a1m6f7G7wT9xC2K5xtqz9zN29kqhLQ1C+Hh3+dtqm79XFinFtC5oklK3G3y12Ruec5CDd3eURj7ZjPUANtCPx52xvavWO7KJ+wvgJwJYnwAehzdL/WUsFDOVGvBmv8WxtnfQJxBKWnDrbtFXO51vwOBIpp4GYepPU48Qv0JHzsC5Nj1p1/YIPgP3PspqObQMfbQsLVTeOL5CmH+NSZn1v/uZjnEv81ztpDUUXRjFqNXqTcfEPX5sRpWGL4V4AMqCtGlfx8J0vrcyVez+/wNErwZ8iR/vWcvj00QChQ5HwDQuurtUnjLzeaenLOoSpmFax3sn0nFivCxKLrmxGqwKLDX3eAF2BO3flaURUNOK1sMKlqZUpEXkvrNDbLoleUTKGC7R3PVgbS06jeZiN+Caw7GBz4hTo6YmwQgd8ZWPc1s31c8QC8xHzDTiU5fQkz4veQgcekXlGenXlz8oddQ/"


NOTIFICATION_TEMPLATES_B64 = "eNq9VcFqGzEQ/ZVhIZCAGze0EDCOIY17TClJmktsFlka20q00iJpHRzjDyk55QPyCT05/a+O1rv2Ol6nh4YaFtaamTczb/Rmb2aRZglGrehMSdQetPFyKDnz0uioEfEx0xoV2b8mTKpwYrSQubUV7fdsTwP9hOGHI/T7vcjiEC1qjjGd+WmKvegATk6gF51dnEMXmepFZRTTohLJM+dNEvO8jhhDOop909czdxeXSaSGm9I7/Cij0S5TPu+lFzU2jd8yb/M+gL/ldsmSVCH5KIW81uNqjJal08p5v75oRykyF0olkuvKZUSbQrGVoWs0voY/qI4i54Dm8X3qx/nYBPMYh9mNUNC5yGgcdJRbpi6WOmZiEtJFrc90ZniWBNILmDCpK6KW3FGzgQoYR/Q+IR8ydwkCvuDQ2ACYoHNsFMLaaadrBnbxCwTqRruZdkKh4SGLXTwJCYMpH5sErhdPCaS/f8rUJPrlUUnQTPDx4ukBbxfPfPEMHm2yeNZwZ/RDmA1HaIIRg5dHm9GbD5RLbL1KsmSo7bw1etSZzXLyvfQ0wPm83SzO2wNbeHZpIEkLyHFIeCkeZl4qd0idJcznjHmZ4H5AKSk8IKQ822bmS0jNg7BsgkkJfy09U6cjBFKWljwErOkqqT5n9k6Y+zAzh1rEbuo8JvGGClsfC6M3MVMqZs7JkUZ0S0s2uKWbSVh5QlhnhAtMpBZo8w6rVFA2i1ymQWmEcjMLf1FO0MaDaby6DkOJKlyfGmUuEVYh1ijqRmdKbSyI4oCXb4Pydd5ftoS2ru5TQXVH88Z6N1UUuuoKPsAxhLv41zUVWn+9MTb0t3NV7F4TwaO/EvhS2lu6rtV0qecc4b1UfPx+Kh5/6vxIuSGSRxs9gy2IbzfJpXL3aQHCkPajud8KCXSDdEClB2KOIRS+qdpMlbJVslNKN9TdWgkWtpRMrjVB1Pd20Nbgd8Z3qcjA7zZGyfzu2OLryZmrCd/4JoYrvRvndKltAd5s4xTCD4ugitBuFhyGZ7YHcrgsGh23Ms3nsDcvZrXqdW1c5ynnUnZdAVguPQIn0RL+3vzdV9lRdZWd1d27f11jFfr+x/rq/wFiHkXT"


CUSTOM_PERMISSION_FIELDS = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"mask",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"impersonate",
)


def _pad_base64(encoded):
	return encoded + ("=" * (-len(encoded) % 4))


def _decode_bundle(encoded):
	return json.loads(zlib.decompress(base64.b64decode(_pad_base64(encoded))).decode("utf-8"))


def _apply_additional_property_setters():
	name = "CRM Organization-annual_revenue-permlevel"
	values = {
		"doctype_or_field": "DocField",
		"doc_type": "CRM Organization",
		"field_name": "annual_revenue",
		"property": "permlevel",
		"property_type": "Int",
		"value": "1",
		"is_system_generated": 0,
	}

	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, values, update_modified=False)
		return

	frappe.get_doc({"doctype": "Property Setter", "name": name, **values}).insert(ignore_permissions=True)


def _apply_custom_docperms():
	for source in _decode_bundle(CUSTOM_DOCPERM_B64):
		filters = {
			"parent": source["parent"],
			"role": source["role"],
			"permlevel": source["permlevel"],
		}
		name = frappe.db.exists("Custom DocPerm", filters)
		values = {
			"if_owner": source.get("if_owner", 0),
			**{field: source.get(field, 0) for field in CUSTOM_PERMISSION_FIELDS},
		}

		if name:
			frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
			continue

		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				**filters,
				**values,
			}
		).insert(ignore_permissions=True)


def _apply_safe_crm_settings():
	if not frappe.db.exists("DocType", "CRM Settings"):
		return

	settings = frappe.get_single("CRM Settings")
	if settings.get("enable_frappe_crm_data_synchronization") != 1:
		settings.enable_frappe_crm_data_synchronization = 1
		settings.save(ignore_permissions=True)


def _apply_safe_erpnext_crm_settings():
	if not frappe.db.exists("DocType", "ERPNext CRM Settings"):
		return

	settings = frappe.get_single("ERPNext CRM Settings")
	targets = {
		"enabled": 1,
		"erpnext_company": "Vital Age Clinic",
		"create_customer_on_status_change": 1,
		"deal_status": "Monitoring",
	}
	changed = False

	for fieldname, value in targets.items():
		if settings.get(fieldname) != value:
			settings.set(fieldname, value)
			changed = True

	# Saving intentionally invokes the CRM integration's own validation so its
	# system-generated fields, quotation filter and Item permissions are created.
	# API credentials and remote-site secrets are never populated here.
	if changed:
		settings.save(ignore_permissions=True)


def _apply_notifications():
	sender = "Vital Age Clinic Admin"
	if not frappe.db.exists("Email Account", sender):
		# Email Account credentials are environment-specific. Re-run migrate after
		# configuring this account on a fresh site to install the notifications.
		return

	for template in _decode_bundle(NOTIFICATION_TEMPLATES_B64):
		name = template["name"]
		if frappe.db.exists("Notification", name):
			continue

		doc = frappe.new_doc("Notification")
		for fieldname, value in template.items():
			if fieldname in {"name", "recipients", "sender"}:
				continue
			doc.set(fieldname, value)

		doc.name = name
		doc.sender = sender
		for recipient in template.get("recipients", []):
			doc.append("recipients", recipient)
		doc.insert(ignore_permissions=True)


def _ensure_administrator_default_views():
	if not frappe.db.exists("DocType", "CRM View Settings"):
		return

	for source in DEFAULT_VIEWS:
		view = frappe._dict(source)
		rows = remove_duplicates(sync_default_rows(view.doctype, view.type) or [])
		columns = sync_default_columns(view) or []

		name = frappe.db.exists(
			"CRM View Settings",
			{
				"dt": view.doctype,
				"type": view.type or "list",
				"is_standard": 1,
				"user": "Administrator",
			},
		)

		doc = frappe.get_doc("CRM View Settings", name) if name else frappe.new_doc("CRM View Settings")
		doc.label = view.label
		doc.type = view.type or "list"
		doc.dt = view.doctype
		doc.user = "Administrator"
		doc.route_name = view.route_name or get_route_name(view.doctype)
		doc.load_default_columns = view.load_default_columns or False
		doc.filters = json.dumps(view.filters or {})
		doc.order_by = view.order_by or "modified desc"
		doc.group_by_field = view.group_by_field or "owner"
		doc.column_field = view.column_field or "status"
		doc.title_field = view.title_field
		doc.kanban_columns = "[]"
		doc.kanban_fields = "[]"
		doc.columns = json.dumps(columns)
		doc.rows = json.dumps(rows)
		doc.is_standard = 1
		doc.is_default = 1

		if name:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)

		frappe.db.set_value(
			"CRM View Settings",
			{
				"name": ("!=", doc.name),
				"user": "Administrator",
				"dt": view.doctype,
				"is_default": 1,
			},
			"is_default",
			0,
			update_modified=False,
		)
