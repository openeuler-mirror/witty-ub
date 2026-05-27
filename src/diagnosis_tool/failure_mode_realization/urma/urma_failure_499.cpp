#include "urma_failure_499.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure499> g_urma("urma_499");

bool UrmaFailure499::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_eid' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter with err dev or ops.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure499::GetName() const
{
    return "设备对象、sysfs设备信息、provider操作表无效导致查询设备失败";
}

std::string UrmaFailure499::GetRootCauseDesc() const
{
    return "函数用于查询设备，调用方传入的设备对象、sysfs设备信息、provider操作表不满足接口前置条件，无法继续完成本次UR"
           "MA操作。";
}

RootCause UrmaFailure499::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure499::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure499::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_eid，Invalid parameter with err dev or ops.。";
}

std::string UrmaFailure499::GetId() const
{
    return "urma_499";
}

} // namespace diag
