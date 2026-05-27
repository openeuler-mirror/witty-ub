#include "urma_failure_112.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure112> g_urma("urma_112");

bool UrmaFailure112::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_update_pjetty_id_mapping' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Failed to add recreated pjetty id mapping: , ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure112::GetName() const
{
    return "物理 Jetty删除时下层资源准备失败";
}

std::string UrmaFailure112::GetRootCauseDesc() const
{
    return "函数负责删除物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure112::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure112::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure112::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_update_pjetty_id_mapping，Failed to add recreated pjetty id "
           "mapping: , ret:。";
}

std::string UrmaFailure112::GetId() const
{
    return "urma_112";
}

} // namespace diag
