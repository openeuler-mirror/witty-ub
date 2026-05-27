#include "urma_failure_061.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure061> g_urma("urma_061");

bool UrmaFailure061::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfr_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create vjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure061::GetName() const
{
    return "虚拟 JFR创建时下层资源准备失败";
}

std::string UrmaFailure061::GetRootCauseDesc() const
{
    return "函数负责创建虚拟 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure061::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure061::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure061::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfr_p_vjetty_info，Failed to create vjfr";
}

std::string UrmaFailure061::GetId() const
{
    return "urma_061";
}

} // namespace diag
