#include "urma_failure_810.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure810> g_urma("urma_810");

bool UrmaFailure810::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure810::GetName() const
{
    return "URMA context无效导致去激活JFS失败";
}

std::string UrmaFailure810::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure810::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure810::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure810::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure810::GetId() const
{
    return "urma_810";
}

} // namespace diag
