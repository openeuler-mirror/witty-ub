#include "urma_failure_599.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure599> g_urma("urma_599");

bool UrmaFailure599::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pjfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete pjfr' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure599::GetName() const
{
    return "物理 JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure599::GetRootCauseDesc() const
{
    return "函数负责释放或撤销物理 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure599::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure599::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure599::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_pjfr，Failed to delete pjfr，, ret:";
}

std::string UrmaFailure599::GetId() const
{
    return "urma_599";
}

} // namespace diag
