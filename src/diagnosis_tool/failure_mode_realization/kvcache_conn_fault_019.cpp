#include "kvcache_conn_fault_019.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault019> g_KvcacheConnFault019("kvcache_conn_fault_019");

KvcacheConnFault019::KvcacheConnFault019() noexcept
{
}

bool KvcacheConnFault019::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L367-L380
    // 来源: 08-fault-triage-consolidated.md L109-L110
    // 来源: 10-customer-fault-scenarios.md L175-L176
    // 验证方法: INFO log含[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]，按zmq_last_error_number对照errno
    // 匹配逻辑: grep `\[ZMQ_SEND_FAILURE_TOTAL\]`或`\[ZMQ_RECEIVE_FAILURE_TOTAL\]` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[ZMQ_SEND_FAILURE_TOTAL\]|\[ZMQ_RECEIVE_FAILURE_TOTAL\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault019::GetName() const
{
    return "ZMQ发送/接收失败";
}

std::string KvcacheConnFault019::GetRootCauseDesc() const
{
    return "zmq_msg_send/recv硬失败，按zmq_last_error_number对照errno确定具体OS原因";
}

RootCause KvcacheConnFault019::AnalyzeRootCause()
{
    return RootCause(true, "zmq_msg_send/recv硬失败，按zmq_last_error_number对照errno确定具体OS原因");
}

std::string KvcacheConnFault019::GetFixSuggDesc() const
{
    return "按errno对照处置。errno对照表：11(EAGAIN背压)、101(ENETUNREACH路由不可达)、104(ECONNRESET对端reset)、110(ETIMEDOUT TCP超时)、111(ECONNREFUSED端口无监听)、113(EHOSTUNREACH主机不可达)";
}

std::string KvcacheConnFault019::GetValidationMethodDesc() const
{
    return "INFO log含[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]，按zmq_last_error_number对照errno";
}

std::string KvcacheConnFault019::GetId() const
{
    return "kvcache_conn_fault_019";
}

} // namespace diag