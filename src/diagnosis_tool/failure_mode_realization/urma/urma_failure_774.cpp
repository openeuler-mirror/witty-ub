#include "urma_failure_774.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure774> g_urma("urma_774");

bool UrmaFailure774::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfc_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure774::GetName() const
{
    return "设置JFC所需输入对象无效导致设置JFC失败";
}

std::string UrmaFailure774::GetRootCauseDesc() const
{
    return "函数用于设置JFC，调用方传入的设置JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure774::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure774::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure774::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfc_opt，Invalid parameter.。";
}

std::string UrmaFailure774::GetId() const
{
    return "urma_774";
}

} // namespace diag
