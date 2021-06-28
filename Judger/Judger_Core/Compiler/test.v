`include "notgate.v"

module top_module();
    reg in0;
    reg in1;
    wire out0;
    wire out1;
    initial begin
        assign in0 = 0;
        assign in1 = 1;
    end
    notgate a(
        .in         (in0),
        .out        (out0)
    ), b(
        .in         (in1),
        .out        (out1)
    );
    always @(*) begin
        $display(out0);
        $display(out1);
    end
endmodule