#include "urma_failure_589.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure589> g_urma("urma_589");

bool UrmaFailure589::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete pjfce.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure589::GetName() const
{
    return "JFCE清理阶段下层释放操作失败";
}

std::string UrmaFailure589::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure589::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure589::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure589::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jfce，Failed to delete pjfce.";
}

std::string UrmaFailure589::GetId() const
{
    return "urma_589";
}

} // namespace diag
