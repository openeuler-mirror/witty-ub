#include "urma_failure_789.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure789> g_urma("urma_789");

bool UrmaFailure789::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, trans_mode:' | grep -F ', order_type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure789::GetName() const
{
    return "执行URMA资源所需输入对象无效导致执行JFS失败";
}

std::string UrmaFailure789::GetRootCauseDesc() const
{
    return "函数用于执行JFS，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure789::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure789::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure789::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_order_type，Invalid parameter, trans_mode:，, order_type:。";
}

std::string UrmaFailure789::GetId() const
{
    return "urma_789";
}

} // namespace diag
