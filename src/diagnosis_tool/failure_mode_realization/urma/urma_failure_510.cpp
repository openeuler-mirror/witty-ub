#include "urma_failure_510.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure510> g_urma("urma_510");

bool UrmaFailure510::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Fail to register vseg, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure510::GetName() const
{
    return "Segment注册时下层资源准备失败";
}

std::string UrmaFailure510::GetRootCauseDesc() const
{
    return "函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure510::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure510::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure510::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vseg，Fail to register vseg, ret:";
}

std::string UrmaFailure510::GetId() const
{
    return "urma_510";
}

} // namespace diag
