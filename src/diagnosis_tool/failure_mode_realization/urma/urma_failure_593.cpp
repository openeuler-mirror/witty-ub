#include "urma_failure_593.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure593> g_urma("urma_593");

bool UrmaFailure593::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete vjfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure593::GetName() const
{
    return "虚拟 JFC清理阶段下层释放操作失败";
}

std::string UrmaFailure593::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure593::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure593::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure593::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jfc，Failed to delete vjfc";
}

std::string UrmaFailure593::GetId() const
{
    return "urma_593";
}

} // namespace diag
