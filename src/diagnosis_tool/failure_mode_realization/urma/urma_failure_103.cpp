#include "urma_failure_103.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure103> g_urma("urma_103");

bool UrmaFailure103::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unregister_health_check_seg_for_jetty' \"$URMA_LOG_PATH\" "
        "2>/dev/null | grep -F 'Failed to unregister health check segment'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure103::GetName() const
{
    return "健康检查清理阶段下层释放操作失败";
}

std::string UrmaFailure103::GetRootCauseDesc() const
{
    return "函数负责释放或撤销健康检查相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure103::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure103::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure103::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unregister_health_check_seg_for_jetty，Failed to unregister "
           "health check segment。";
}

std::string UrmaFailure103::GetId() const
{
    return "urma_103";
}

} // namespace diag
