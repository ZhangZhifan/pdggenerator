int func(int param1) {
    int a = param1;
    int b;
    int c = 0;
    int d = 0;
    for (b = 0; b < 10; b++) {
        if (a >= 20)
            break;
        if (b == 5)
            continue;
        if (c % 2) {
            d += 2;
        }
        else
            d += 2;
        c += 1;
    }
    printf("%d\n", c);
}