#include "urma_failure_198.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure198> g_urma("urma_198");

bool UrmaFailure198::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'[DRV_ERR]create_jetty failed, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure198::GetName() const
{
    return "Jetty创建时下层资源准备失败";
}

std::string UrmaFailure198::GetRootCauseDesc() const
{
    return "函数负责创建Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure198::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure198::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure198::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_jfc，[DRV_ERR]create_jetty failed, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure198::GetId() const
{
    return "urma_198";
}

} // namespace diag
