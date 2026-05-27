#include "urma_failure_685.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure685> g_urma("urma_685");

bool UrmaFailure685::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfce' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure685::GetName() const
{
    return "URMA context、provider操作表、provider未提供delete_jfce操作实现无效导致删除JFCE失败";
}

std::string UrmaFailure685::GetRootCauseDesc() const
{
    return "函数用于删除JFCE，调用方传入的URMA "
           "context、provider操作表、provider未提供delete_jfce操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure685::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure685::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure685::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfce，Invalid parameter.。";
}

std::string UrmaFailure685::GetId() const
{
    return "urma_685";
}

} // namespace diag
