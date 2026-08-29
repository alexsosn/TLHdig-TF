# Crossing-tag repairs: for philological review

These patches do not merely escape a character or close a stray tag. They **choose
where an element boundary lands**, and XML validity cannot tell whether the editor
meant to move the wrapper or the word. A specialist should confirm each before the
dataset is deposited.

Every other patch class is mechanical (escaping, deleting a stray fragment) and is not
listed here.

| # | file | patch | element closed early | old | new |
|---|---|---|---|---|---|
| 1 | `CTH 144_XML_SVH/KUB 26.29+.xml` | 0 | `AO:Akkgram` | `</w> <w>Ù</w> <w>A-NA</AO:Akkgram></w> <w><` | `</AO:Akkgram></w> <w>Ù</w> <w>A-NA</AO:Akkgram></w> <w><` |
| 2 | `CTH 209_XML_TLH/KBo 12.55.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 3 | `CTH 294_XML_TLH/KBo 31.43.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 4 | `CTH 297_XML_TLH/KBo 31.47.xml` | 4 | `w` | `</text>` | `</w></w></text>` |
| 5 | `CTH 297_XML_TLH/KBo 8.30.xml` | 2 | `w` | `</text>` | `</w></w></text>` |
| 6 | `CTH 324_XML_MYTH/IBoT 3.141.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 7 | `CTH 324_XML_MYTH/KUB 33.5.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 8 | `CTH 334_XML_MYTH/KBo 52.9.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 9 | `CTH 336_XML_MYTH/KUB 33.57.xml` | 0 | `AO:KolonNr` | `</w> </AO:KolonNr></w>  <lb txtid="KUB 33.57" lnr="Vs. II 1′" lg="Hit"` | `</AO:KolonNr></w> </AO:KolonNr></w>  <lb txtid="KUB 33.57" lnr="Vs. II` |
| 10 | `CTH 336_XML_MYTH/KUB 33.57.xml` | 3 | `AO:KolonNr` | `</w> </AO:KolonNr></w>  <lb txtid="KUB 33.57` | `</AO:KolonNr></w> </AO:KolonNr></w>  <lb txtid="KUB 33.57` |
| 11 | `CTH 336_XML_MYTH/KUB 33.60.xml` | 0 | `AO:KolonNr` | `</w> </AO:KolonNr></w>  <lb txtid="KUB 33.60` | `</AO:KolonNr></w> </AO:KolonNr></w>  <lb txtid="KUB 33.60` |
| 12 | `CTH 341_XML_MYTH/KBo 22.91.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 13 | `CTH 341_XML_MYTH/KUB 60.14.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 14 | `CTH 345_XML_MYTH/KUB 33.98.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 15 | `CTH 381_XML_GEBET/KUB 6.46.xml` | 1 | `sGr` | `</d>a-la-a-aš</w> <w trans="10" mrp0sel=" "` | `</sGr></d>a-la-a-aš</w> <w trans="10" mrp0sel=" "` |
| 16 | `CTH 394_XML_BESRIT/Bo 3353.xml` | 0 | `w` | `</text>` | `</w></w></w></w></w></text>` |
| 17 | `CTH 409_XML_BESRIT/KBo 53.35+.xml` | 0 | `AO:HitGLOS` | `</w> <w trans="pattanzi" mrp0sel=" 1 " mrp1="padd=a-@graben@3PL.PRS@II` | `</AO:HitGLOS></w> <w trans="pattanzi" mrp0sel=" 1 " mrp1="padd=a-@grab` |
| 18 | `CTH 409_XML_BESRIT/KBo 53.35+.xml` | 2 | `AO:HitGLOS` | `</w> <w mrp0sel="DEL">ḫi-im-ma-x<del_in/><` | `</AO:HitGLOS></w> <w mrp0sel="DEL">ḫi-im-ma-x<del_in/><` |
| 19 | `CTH 409_XML_BESRIT/KBo 53.35+.xml` | 4 | `AO:HitGLOS` | `</w> <w trans="nat" mrp0sel=" " mrp1="n=at@@` | `</AO:HitGLOS></w> <w trans="nat" mrp0sel=" " mrp1="n=at@@` |
| 20 | `CTH 409_XML_BESRIT/KBo 53.35+.xml` | 6 | `AO:HitGLOS` | `</w> <w trans="taknaš" mrp0sel=" 1 " mrp1="` | `</AO:HitGLOS></w> <w trans="taknaš" mrp0sel=" 1 " mrp1="` |
| 21 | `CTH 411_XML_BESRIT/KBo 41.40+.xml` | 0 | `w` | `</text>` | `</w></w></w></w></w></w></w></text>` |
| 22 | `CTH 412_XML_TLH/KBo 38.169.xml` | 0 | `AO:TxtPubl` | `</AO:Manuscripts> <AO:Manuscripts><AO:TxtPubl>x+2 mu-k<de` | `</AO:TxtPubl></AO:Manuscripts> <AO:Manuscripts><AO:TxtPubl>x+2 mu-k<de` |
| 23 | `CTH 412_XML_TLH/KBo 38.169.xml` | 1 | `AO:TxtPubl` | `</AO:Manuscripts> <AO:Manuscripts><AO:TxtPubl>3' <space c` | `</AO:TxtPubl></AO:TxtPubl></AO:Manuscripts> <AO:Manuscripts><AO:TxtPub` |
| 24 | `CTH 412_XML_TLH/KBo 38.169.xml` | 2 | `AO:TxtPubl` | `</AO:Manuscripts> <AO:Manuscripts><AO:TxtPubl>4' <space c` | `</AO:TxtPubl></AO:TxtPubl></AO:TxtPubl></AO:TxtPubl></AO:Manuscripts> ` |
| 25 | `CTH 412_XML_TLH/KBo 38.169.xml` | 3 | `AO:TxtPubl` | `</AO:Manuscripts> <AO:Manuscripts><AO:TxtPubl>5' <del_fin` | `</AO:TxtPubl></AO:TxtPubl></AO:TxtPubl></AO:Manuscripts> <AO:Manuscrip` |
| 26 | `CTH 412_XML_TLH/KBo 38.169.xml` | 4 | `AO:TxtPubl` | `</AO:Manuscripts> <AO:Manuscripts><AO:TxtPubl>6' <space c` | `</AO:TxtPubl></AO:TxtPubl></AO:TxtPubl></AO:TxtPubl></AO:Manuscripts> ` |
| 27 | `CTH 412_XML_TLH/KBo 38.169.xml` | 5 | `AO:TxtPubl` | `</AO:Manuscripts> </text></div1></body></AOxml> ` | `</AO:TxtPubl></AO:TxtPubl></AO:Manuscripts> </text></div1></body></AOx` |
| 28 | `CTH 420_XML_TLH/KBo 53.31.xml` | 0 | `AO:AkkGLOS` | `</w> <w trans="ta~" mrp0sel="DEL"><d>GIŠ</d` | `</AO:AkkGLOS></AO:AkkGLOS></AO:AkkGLOS></w> <w trans="ta~" mrp0sel="DE` |
| 29 | `CTH 445_XML_BESRIT/KBo 59.9.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 30 | `CTH 448_XML_BESRIT/KBo 10.36.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 31 | `CTH 450_XML_BESRIT/KUB 12.22.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 32 | `CTH 458_XML_BESRIT/KBo 56.227.xml` | 0 | `AO:HitGLOS` | `</w> <w><space c="23"/></w> <w mrp0sel="DEL"><del_fin/>x</w> <w mrp0se` | `</AO:HitGLOS></w> <w><space c="23"/></w> <w mrp0sel="DEL"><del_fin/>x<` |
| 33 | `CTH 458_XML_BESRIT/KBo 56.227.xml` | 2 | `AO:HitGLOS` | `</w> <w><space c="22"/></w> <w mrp0sel="DEL"` | `</AO:HitGLOS></w> <w><space c="22"/></w> <w mrp0sel="DEL"` |
| 34 | `CTH 458_XML_BESRIT/KBo 56.227.xml` | 4 | `AO:HitGLOS` | `</w> <w><space c="23"/></w> <w mrp0sel="DEL"><del_fin/>x</w> <w mrp0se` | `</AO:HitGLOS></w> <w><space c="23"/></w> <w mrp0sel="DEL"><del_fin/>x<` |
| 35 | `CTH 460_XML_TLH/KBo 56.45.xml` | 0 | `AO:HitGLOS` | `</w> <w><space c="41"/></w> <w><del_fin/></A` | `</AO:HitGLOS></w> <w><space c="41"/></w> <w><del_fin/></A` |
| 36 | `CTH 460_XML_TLH/KBo 56.45.xml` | 2 | `AO:HitGLOS` | `</w> <w mrp0sel="DEL">x x</w> <w mrp0sel="DE` | `</AO:HitGLOS></w> <w mrp0sel="DEL">x x</w> <w mrp0sel="DE` |
| 37 | `CTH 470_XML_TLH/DBH 46_2.51.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 38 | `CTH 470_XML_TLH/IBoT 4.286.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 39 | `CTH 479_XML_BESRIT/KBo 41.49+.xml` | 0 | `w` | `</text>` | `</w></w></w></w></w></w></w></w></w></w></w></w></w></w></text>` |
| 40 | `CTH 479_XML_BESRIT/KBo 54.68.xml` | 0 | `w` | `</text>` | `</w></w></w></w></text>` |
| 41 | `CTH 487_XML_BESRIT/KUB 12.24.xml` | 0 | `w` | `</text>` | `</w></w></w></w></w></w></w></text>` |
| 42 | `CTH 495_XML_BESRIT/KUB 39.54+.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 43 | `CTH 526_XML_KULTINV/KBo 49.310.xml` | 0 | `w` | `</text>` | `</w></w></text>` |
| 44 | `CTH 526_XML_KULTINV/KUB 38.29.xml` | 2 | `w` | `</text>` | `</w></w></text>` |
| 45 | `CTH 527_XML_KULTINV/DAAM 1.39.xml` | 4 | `w` | `</text>` | `</w></w></text>` |
| 46 | `CTH 527_XML_KULTINV/KUB 38.7.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 47 | `CTH 528_XML_KULTINV/DAAM 1.51.xml` | 1 | `w` | `</text>` | `</w></text>` |
| 48 | `CTH 528_XML_KULTINV/KBo 22.222.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 49 | `CTH 528_XML_KULTINV/KBo 26.205.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 50 | `CTH 528_XML_KULTINV/KBo 54.164.xml` | 0 | `w` | `</text>` | `</w></w></text>` |
| 51 | `CTH 528_XML_KULTINV/KUB 56.39.xml` | 2 | `w` | `</text>` | `</w></w></w></w></w></w></text>` |
| 52 | `CTH 529_XML_KULTINV/DAAM 1.36.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 53 | `CTH 529_XML_KULTINV/KUB 53.21.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 54 | `CTH 530_XML_KULTINV/KBo 13.252.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 55 | `CTH 544_XML_HDivT/KUB 34.22+.xml` | 1 | `w` | `</text>` | `</w></text>` |
| 56 | `CTH 570_XML_HDivT/KBo 58.79+.xml` | 13 | `w` | `</text>` | `</w></w></w></w></w></text>` |
| 57 | `CTH 570_XML_HDivT/KUB 50.123.xml` | 1 | `w` | `</text>` | `</w></text>` |
| 58 | `CTH 577_XML_HDivT/AT 454.xml` | 0 | `sGr` | `</w> <w trans="ZI" mrp0sel=" " mrp1="① ZI@` | `</sGr></w> <w trans="ZI" mrp0sel=" " mrp1="① ZI@` |
| 59 | `CTH 580_XML_HDivT/KBo 53.110+.xml` | 1 | `w` | `</text>` | `</w></text>` |
| 60 | `CTH 582_XML_TLH/IBoT 4.45.xml` | 1 | `w` | `</text>` | `</w></text>` |
| 61 | `CTH 585_XML_HDivT/585_u+.xml` | 1 | `w` | `</text>` | `</w></text>` |
| 62 | `CTH 641_XML_BESRIT/KBo 21.42.xml` | 0 | `w` | `</text>` | `</w></w></text>` |
| 63 | `CTH 72_XML_TLH/KUB 19.15+.xml` | 0 | `AO:Manuscripts` | `</text>` | `</AO:Manuscripts></text>` |
| 64 | `CTH 734_XML_TLH/KBo 37.21.xml` | 4 | `w` | `</text>` | `</w></w></text>` |
| 65 | `CTH 756_XML_TLH/KBo 29.31+.xml` | 2 | `w` | `</text>` | `</w></w></text>` |
| 66 | `CTH 812_XML_TLH/KBo 36.30.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 67 | `CTH 819_XML_TLH/KUB 4.89.xml` | 0 | `AO:TabSep` | `</w> <w><space c="18"/></w> <w trans="\|" mrp` | `</AO:TabSep></w> <w><space c="18"/></w> <w trans="\|" mrp` |
| 68 | `CTH 820_XML_TLH/KUB 48.15.xml` | 0 | `w` | `</text>` | `</w></text>` |
| 69 | `CTH 831_XML_TLH/IBoT 4.235.xml` | 4 | `AO:--italic` | `</w> <parsep/> <w lg="Lin"></AO:--italic></w` | `</AO:--italic></w> <parsep/> <w lg="Lin"></AO:--italic></w` |
| 70 | `CTH 831_XML_TLH/IBoT 4.249.xml` | 4 | `AO:--italic` | `</w> <parsep/> <w lg="Lin"></AO:--italic></w` | `</AO:--italic></w> <parsep/> <w lg="Lin"></AO:--italic></w` |
| 71 | `CTH 831_XML_TLH/KBo 41.121.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 72 | `CTH 832_XML_TLH/KBo 16.45.xml` | 2 | `w` | `</text>` | `</w></text>` |
| 73 | `CTH 832_XML_TLH/KBo 71.216.xml` | 1 | `AO:TxtPubl` | `</AO:Manuscripts>` | `</AO:TxtPubl></AO:Manuscripts>` |
| 74 | `CTH 832_XML_TLH/UBT 70.xml` | 2 | `w` | `</text>` | `</w></text>` |
