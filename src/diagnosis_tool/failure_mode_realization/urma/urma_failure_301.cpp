#include "urma_failure_301.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure301> g_urma("urma_301");

bool UrmaFailure301::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_grp' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure301::GetName() const
{
    return "URMA context、provider操作表、Segment对象、provider未提供import_seg操作实现无效导致删除Jetty失败";
}

std::string UrmaFailure301::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA "
           "context、provider操作表、Segment对象、provider未提供import_"
           "seg操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure301::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure301::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure301::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_grp，Invalid parameter.。";
}

std::string UrmaFailure301::GetId() const
{
    return "urma_301";
}

} // namespace diag
