#include "urma_failure_761.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure761> g_urma("urma_761");

bool UrmaFailure761::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_trans_mode_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure761::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfc操作实现无效导致创建JFC失败";
}

std::string UrmaFailure761::GetRootCauseDesc() const
{
    return "函数用于创建JFC，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_"
           "jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure761::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure761::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure761::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_trans_mode_valid，Invalid parameter.";
}

std::string UrmaFailure761::GetId() const
{
    return "urma_761";
}

} // namespace diag
