#include "urma_failure_353.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure353> g_urma("urma_353");

bool UrmaFailure353::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_set_bonding_mode' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create pctx when set bonding mode, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure353::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure353::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure353::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure353::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure353::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Failed to create pctx when set bonding mode, "
           "ret:。";
}

std::string UrmaFailure353::GetId() const
{
    return "urma_353";
}

} // namespace diag
