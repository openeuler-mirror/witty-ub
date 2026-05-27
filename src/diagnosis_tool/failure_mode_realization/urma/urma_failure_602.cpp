#include "urma_failure_602.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure602> g_urma("urma_602");

bool UrmaFailure602::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete pjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure602::GetName() const
{
    return "物理 JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure602::GetRootCauseDesc() const
{
    return "函数负责释放或撤销物理 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure602::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure602::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure602::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jfr，Failed to delete pjfr";
}

std::string UrmaFailure602::GetId() const
{
    return "urma_602";
}

} // namespace diag
