#include "urma_failure_253.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure253> g_urma("urma_253");

bool UrmaFailure253::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty") != std::string::npos &&
           message.find("[DRV_ERR]create_jetty failed, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure253::GetName() const
{
    return "下层资源创建失败导致创建Jetty失败";
}

std::string UrmaFailure253::GetRootCauseDesc() const
{
    return "urma_create_jetty在创建Jetty过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure253::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure253::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure253::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty，[DRV_ERR]create_jetty failed, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure253::GetId() const
{
    return "urma_253";
}
} // namespace diag
