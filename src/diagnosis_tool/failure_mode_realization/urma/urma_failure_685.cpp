#include "urma_failure_685.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure685> g_urma("urma_685");

bool UrmaFailure685::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_device_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'max eid cnt' | grep -F 'is err'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure685::GetName() const
{
    return "释放EID过程中依赖步骤失败";
}

std::string UrmaFailure685::GetRootCauseDesc() const
{
    return "函数用于释放EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure685::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure685::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure685::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_device_list，max eid cnt，is err";
}

std::string UrmaFailure685::GetId() const
{
    return "urma_685";
}

} // namespace diag
