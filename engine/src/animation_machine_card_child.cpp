#include "animation_machine_internal.h"
namespace ms5 {
// Card child callback c250 and its scene preparation helper de424/e7c16.
// JSR a29c (card menu) has no executor: only a caller stop there succeeds.
bool animation_card_child_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0xc250:r.d[0]=0xffffffe1U;r.d[1]=0xffffffe1U;r.d[2]=0xffffffe1U;r.d[3]=0;r.pc=0xc258;return true;
    case 0xc258:return am_call(c,0x8c16,0xc25e);
    case 0xc25e:
        if(!am_write(c,r.a[6],4,0xc266))return false;r.pc=0xc264;return true;
    case 0xc264:case 0xc28e:case 0xde48a:return am_return(c);
    case 0xc266:return am_call(c,0xde424,0xc26c);
    case 0xc26c:r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=0x14;r.pc=0xc274;return true;
    case 0xc274:return am_call(c,0x8c16,0xc27a);
    // MOVE.W #14,7e(A6); MOVE.L #c286,(A6); execution falls into c286.
    case 0xc27a:
        if(!am_write(c,r.a[6]+0x7eU,2,0x14))return false;r.pc=0xc280;return true;
    case 0xc280:
        if(!am_write(c,r.a[6],4,0xc286))return false;r.pc=0xc286;return true;
    // SUBQ.W #1,7e(A6) and BCS.W: C is the unsigned borrow (old WORD 0), consumed here only.
    case 0xc286:
        if(!am_read(c,r.a[6]+0x7eU,2,value))return false;
        if(!am_write(c,r.a[6]+0x7eU,2,(value-1U)&65535U))return false;r.pc=value==0?0xc290:0xc28e;return true;
    // Each instruction is its own block: native split checkpoints stop at c296/c29a/c29e.
    case 0xc290:
        if(!am_write(c,r.a[6]+0x80U,1,0))return false;r.pc=0xc296;return true;
    case 0xc296:
        if(!am_read(c,r.a[6]+0x76U,4,value))return false;r.a[0]=value;r.pc=0xc29a;return true;
    case 0xc29a:
        if(!am_read(c,r.a[6]+0x7aU,2,value))return false;am_word(r.d[0],value);r.pc=0xc29e;return true;
    case 0xc29e:
        if(!am_read(c,r.a[6]+0x7cU,2,value))return false;am_word(r.d[1],value);r.pc=0xc2a2;return true;
    case 0xc2a2:return am_call(c,0xa29c,0xc2a8);
    case 0xde424:return am_call(c,0xe7c16,0xde42a);
    case 0xde42a:am_word(r.d[0],0x49);r.pc=0xde42e;return true;
    case 0xde42e:
        if(!am_zero_bank(c))return false;r.pc=0xde444;return true; // A5-7ff0 uses live A5.
    // MOVEA.L 20000c,A0 (current bank); LSL.W #2,D0; MOVEA.L 0(A0,D0.W),A0.
    case 0xde444:
        if(!am_read(c,0x20000c,4,value))return false;r.a[0]=value;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;r.pc=0xde450;return true;
    case 0xde450:return am_call(c,0x8da2,0xde456);
    case 0xde456:r.a[0]=0xde40c;r.pc=0xde45a;return true;
    case 0xde45a:return am_call(c,0x43ffc,0xde460);
    case 0xde460:r.a[0]=0x109156;r.pc=0xde466;return true;
    case 0xde466:return am_call(c,0x16fac,0xde46c);
    case 0xde46c:r.a[1]=0xde41c;r.a[2]=0;r.pc=0xde474;return true; // LEA; MOVEA.W #0 sign-extends.
    case 0xde474:r.d[0]=0;r.d[1]=31;r.pc=0xde478;return true;
    case 0xde478:return am_call(c,0x16ff8,0xde47e);
    case 0xde47e:return am_call(c,0x1861a,0xde484);
    case 0xde484:return am_call(c,0x17012,0xde48a);
    case 0xe7c16:return am_call(c,0xe7bf4,0xe7c1a);
    case 0xe7c1a:r.a[0]=0xe7bc0;r.pc=0xe7c1e;return true;
    case 0xe7c1e:return am_call(c,0x8da2,0xe7c24);
    case 0xe7c24:am_word(r.d[0],0xfe);am_word(r.d[1],1);am_word(r.d[2],12);r.pc=0xe7c30;return true;
    case 0xe7c30:r.pc=0x8cda;return true;
    default:return am_error(c,"unsupported animation card child PC");
    }
}
}
