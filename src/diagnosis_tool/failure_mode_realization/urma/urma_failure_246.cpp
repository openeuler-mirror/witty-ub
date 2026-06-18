#include "urma_failure_246.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure246> g_urma("urma_246");

bool UrmaFailure246::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfr") != std::string::npos &&
           message.find("[DRV_ERR]Failed to create jfr, dev_name:") != std::string::npos &&
           message.find(", eid_idex:") != std::string::npos;
}

std::string UrmaFailure246::GetName() const
{
    return "下层资源创建失败导致创建JFR失败";
}

std::string UrmaFailure246::GetRootCauseDesc() const
{
    return "urma_create_jfr在创建JFR过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure246::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure246::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure246::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfr，[DRV_ERR]Failed to create jfr, dev_name:，, "
           "eid_idex:。";
}

std::string UrmaFailure246::GetId() const
{
    return "urma_246";
}
} // namespace diag
