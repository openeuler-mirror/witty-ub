#include "urma_failure_086.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure086> g_urma("urma_086");

bool UrmaFailure086::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to register health check task'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure086::GetName() const
{
    return "健康检查注册时下层资源准备失败";
}

std::string UrmaFailure086::GetRootCauseDesc() const
{
    return "函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure086::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure086::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure086::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pjetty，Failed to register health check task";
}

std::string UrmaFailure086::GetId() const
{
    return "urma_086";
}

} // namespace diag
