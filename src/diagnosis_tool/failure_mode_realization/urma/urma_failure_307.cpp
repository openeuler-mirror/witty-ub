#include "urma_failure_307.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure307> g_urma("urma_307");

bool UrmaFailure307::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tpn' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to get "
        "netaddr list, ret:' | grep -F ', max_netaddr_cnt:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure307::GetName() const
{
    return "获取TPN过程中依赖步骤失败";
}

std::string UrmaFailure307::GetRootCauseDesc() const
{
    return "函数用于获取TPN，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure307::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure307::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure307::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tpn，Failed to get netaddr list, ret:，, max_netaddr_cnt:。";
}

std::string UrmaFailure307::GetId() const
{
    return "urma_307";
}

} // namespace diag
