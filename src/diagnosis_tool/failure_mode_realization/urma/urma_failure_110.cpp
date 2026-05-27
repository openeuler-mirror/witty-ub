#include "urma_failure_110.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure110> g_urma("urma_110");

bool UrmaFailure110::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_update_pjetty_id_mapping' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add recreated pjetty id mapping: , ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure110::GetName() const
{
    return "物理 Jetty删除时下层资源准备失败";
}

std::string UrmaFailure110::GetRootCauseDesc() const
{
    return "函数负责删除物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure110::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure110::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure110::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_update_pjetty_id_mapping，Failed to add recreated pjetty id mapping: , "
           "ret:";
}

std::string UrmaFailure110::GetId() const
{
    return "urma_110";
}

} // namespace diag
