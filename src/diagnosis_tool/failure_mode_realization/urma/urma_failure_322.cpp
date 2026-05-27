#include "urma_failure_322.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure322> g_urma("urma_322");

bool UrmaFailure322::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_vjfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create vjfce.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure322::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure322::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure322::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure322::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure322::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_vjfce，Failed to create vjfce.";
}

std::string UrmaFailure322::GetId() const
{
    return "urma_322";
}

} // namespace diag
