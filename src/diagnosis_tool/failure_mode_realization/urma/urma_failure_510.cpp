#include "urma_failure_510.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure510> g_urma("urma_510");

bool UrmaFailure510::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_health_check_tseg' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to unimport health check seg ('");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure510::GetName() const
{
    return "健康检查清理阶段下层释放操作失败";
}

std::string UrmaFailure510::GetRootCauseDesc() const
{
    return "函数负责释放或撤销健康检查相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure510::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure510::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure510::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_health_check_tseg，Failed to unimport health check seg "
           "(。";
}

std::string UrmaFailure510::GetId() const
{
    return "urma_510";
}

} // namespace diag
