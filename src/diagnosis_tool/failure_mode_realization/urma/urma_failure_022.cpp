#include "urma_failure_022.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure022> g_urma("urma_022");

bool UrmaFailure022::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create global context.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure022::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure022::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure022::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure022::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure022::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_init，Failed to create global context.";
}

std::string UrmaFailure022::GetId() const
{
    return "urma_022";
}

} // namespace diag
