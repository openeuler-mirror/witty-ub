#include "urma_failure_328.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure328> g_urma("urma_328");

bool UrmaFailure328::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pjfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create pjfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure328::GetName() const
{
    return "物理 JFC创建时下层资源准备失败";
}

std::string UrmaFailure328::GetRootCauseDesc() const
{
    return "函数负责创建物理 JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure328::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure328::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure328::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfc，Failed to create pjfc。";
}

std::string UrmaFailure328::GetId() const
{
    return "urma_328";
}

} // namespace diag
