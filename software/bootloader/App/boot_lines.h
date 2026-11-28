/* boot_lines.h — 書き込みの待ちで受ける行の処理 */
#ifndef BOOT_LINES_H
#define BOOT_LINES_H

/* 1 行を処理する(行は書きかえてよい) */
void boot_lines_handle(char *line);

/* fw end で書き終わったか(1 = 走るプログラムへ移ってよい) */
int boot_lines_finished(void);

#endif
