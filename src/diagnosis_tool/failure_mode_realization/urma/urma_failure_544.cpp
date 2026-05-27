#include "urma_failure_544.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure544> g_urma("urma_544");

bool UrmaFailure544::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unregister_seg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure544::GetName() const
{
    return "URMA "
           "context、设备对象、provider操作表、Segment对象、provider未提供unregister_"
           "seg操作实现无效导致注销Segment失败";
}

std::string UrmaFailure544::GetRootCauseDesc() const
{
    return "函数用于注销Segment，调用方传入的URMA "
           "context、设备对象、provider操作表、Segment对象、provider未提供unregister_"
           "seg操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure544::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure544::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure544::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unregister_seg，Invalid parameter.。";
}

std::string UrmaFailure544::GetId() const
{
    return "urma_544";
}

} // namespace diag
