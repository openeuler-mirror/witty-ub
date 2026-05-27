#include "urma_failure_342.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure342> g_urma("urma_342");

bool UrmaFailure342::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vcontext' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create context, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure342::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure342::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure342::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure342::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure342::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vcontext，Failed to create context, ret:";
}

std::string UrmaFailure342::GetId() const
{
    return "urma_342";
}

} // namespace diag
