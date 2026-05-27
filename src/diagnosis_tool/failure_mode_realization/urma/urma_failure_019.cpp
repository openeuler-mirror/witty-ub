#include "urma_failure_019.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure019> g_urma("urma_019");

bool UrmaFailure019::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_provider_bond_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Provider Bond register ops failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure019::GetName() const
{
    return "设备注册时下层资源准备失败";
}

std::string UrmaFailure019::GetRootCauseDesc() const
{
    return "函数负责注册设备，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure019::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure019::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure019::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_provider_bond_init，Provider Bond register ops failed.";
}

std::string UrmaFailure019::GetId() const
{
    return "urma_019";
}

} // namespace diag
