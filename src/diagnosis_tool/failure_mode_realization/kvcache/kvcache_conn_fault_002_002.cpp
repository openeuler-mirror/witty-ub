#include "kvcache_conn_fault_002_002.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_002 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248)
static AutoRegister<KvcacheConnFault002_002> g_kvcacheconnfault002_002("kvcache_conn_fault_002_002");

bool KvcacheConnFault002_002::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -h 'ConnectOptions was not configured' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_002::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248
    return "respMsg未配置Init故障";
}

std::string KvcacheConnFault002_002::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248
    return "未配置Init就发起调用，属于用户侧问题。（来源：08手册:L248）";
}

RootCause KvcacheConnFault002_002::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_002::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248
    return "检查业务侧Init调用是否正确配置ConnectOptions。（来源：08手册:L248）";
}

std::string KvcacheConnFault002_002::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L151, L153, L248
    return "通过日志关键字识别（来源：08手册:L248）：匹配ConnectOptions was not configured。（来源：08手册:L248）";
}

std::string KvcacheConnFault002_002::GetId() const
{
    return "kvcache_conn_fault_002_002";
}

} // namespace diag
