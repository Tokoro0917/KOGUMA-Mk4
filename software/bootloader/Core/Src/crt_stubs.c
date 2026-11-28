/*
 * crt_stubs.c — C のライブラリの起動の部品(-nostartfiles で外したもの)の、空の代わり
 *
 * ブートローダは自分の startup(startup_stm32h562xx.s)から main を呼ぶので、C のライブラリの起動の部品(crt0)は使わない。
 * crt0 を入れると、使わないファイルの読み書きの関数まで入ってきて、リンクの警告が出るため。
 * startup が呼ぶ __libc_init_array は _init を呼ぶので、何もしない _init と _fini を置く。
 */
void _init(void)
{
}

void _fini(void)
{
}
