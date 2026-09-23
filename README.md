# Fruit Star

과일을 모아 터뜨리는 HTML5 캔버스 퍼즐. 모바일 세로와 데스크톱 16:9를 모두 지원하며,
빌드 도구 없이 `index.html` 한 파일로 동작합니다.

- 플레이: https://giftpen.github.io/fruit-star/
- 개인정보처리방침: https://giftpen.github.io/fruit-star/privacy.html
- 변경 이력: [CHANGELOG.md](CHANGELOG.md)

## 개발

로컬 서버를 띄운 뒤 검사를 돌립니다. `tools/all.sh` 는 zsh 전용입니다.

```sh
python3 -m http.server 8899 &
zsh tools/all.sh
```
