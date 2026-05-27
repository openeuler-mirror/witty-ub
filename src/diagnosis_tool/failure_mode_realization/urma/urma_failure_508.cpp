#include "urma_failure_508.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure508> g_urma("urma_508");

bool UrmaFailure508::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to register pseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure508::GetName() const
{
    return "Segment注册时下层资源准备失败";
}

std::string UrmaFailure508::GetRootCauseDesc() const
{
    return "函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure508::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure508::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure508::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_pseg，Failed to register pseg";
}

std::string UrmaFailure508::GetId() const
{
    return "urma_508";
}

} // namespace diag
