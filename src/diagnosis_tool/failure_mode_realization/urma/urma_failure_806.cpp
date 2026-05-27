#include "urma_failure_806.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure806> g_urma("urma_806");

bool UrmaFailure806::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure806::GetName() const
{
    return "provider操作表、JFS对象无效导致去激活JFS失败";
}

std::string UrmaFailure806::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure806::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure806::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure806::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，Invalid parameter.。";
}

std::string UrmaFailure806::GetId() const
{
    return "urma_806";
}

} // namespace diag
