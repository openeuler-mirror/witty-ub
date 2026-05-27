#include "urma_failure_676.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure676> g_urma("urma_676");

bool UrmaFailure676::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure676::GetName() const
{
    return "URMA context、设备对象无效导致删除JFCE失败";
}

std::string UrmaFailure676::GetRootCauseDesc() const
{
    return "函数用于删除JFCE，调用方传入的URMA context、设备对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure676::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure676::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure676::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfce，Invalid parameter.";
}

std::string UrmaFailure676::GetId() const
{
    return "urma_676";
}

} // namespace diag
