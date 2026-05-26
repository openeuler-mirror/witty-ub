#include "kvcache_conn_fault_012_002.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_012_002 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272)
static AutoRegister<KvcacheConnFault012_002> g_kvcacheconnfault012_002("kvcache_conn_fault_012_002");

bool KvcacheConnFault012_002::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E 'zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total' $WITTY_UB_WORKER_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault012_002::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272
    return "ZMQ相关问题（重建/断开/握手）";
}

std::string KvcacheConnFault012_002::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272
    return "分为两种情况（来源：08手册:L272）：低频出现SDK自重连可忽略；高频出现转OS查网络；握手失败查TLS/认证配置。";
}

RootCause KvcacheConnFault012_002::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_002::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272
    return "低频可忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置。（来源：08手册:L272）";
}

std::string KvcacheConnFault012_002::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L541, L544-546, L272
    return "通过日志关键字识别（来源：08手册:L272）：匹配zmq_gateway_recreate_total / zmq_event_disconnect_total / zmq_event_handshake_failure_total增多。（来源：08手册:L272）";
}

std::string KvcacheConnFault012_002::GetId() const
{
    return "kvcache_conn_fault_012_002";
}

} // namespace diag
