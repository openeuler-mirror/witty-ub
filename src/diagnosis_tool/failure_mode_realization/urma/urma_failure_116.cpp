#include "urma_failure_116.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure116> g_urma("urma_116");

bool UrmaFailure116::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_import_pseg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'No valid direct route'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure116::GetName() const
{
    return "未找到可用于导入路由的有效对象或路由";
}

std::string UrmaFailure116::GetRootCauseDesc() const
{
    return "函数在导入路由过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure116::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure116::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure116::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_pseg，No valid direct route。";
}

std::string UrmaFailure116::GetId() const
{
    return "urma_116";
}

} // namespace diag
