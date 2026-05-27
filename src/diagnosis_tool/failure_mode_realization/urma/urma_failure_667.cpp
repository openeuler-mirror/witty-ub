#include "urma_failure_667.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure667> g_urma("urma_667");

bool UrmaFailure667::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to free jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure667::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure667::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure667::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure667::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure667::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jfr，Failed to free jfr.";
}

std::string UrmaFailure667::GetId() const
{
    return "urma_667";
}

} // namespace diag
