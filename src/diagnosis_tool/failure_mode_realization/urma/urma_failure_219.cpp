#include "urma_failure_219.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure219> g_urma("urma_219");

bool UrmaFailure219::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("convert_bond_port_id_to_active_index") != std::string::npos &&
           message.find("Invalid primary chip_id:") != std::string::npos;
}

std::string UrmaFailure219::GetName() const
{
    return "convert、Bond资源、端口状态不满足要求导致激活convert、Bond资源、端口失败";
}

std::string UrmaFailure219::GetRootCauseDesc() const
{
    return "convert_bond_port_id_to_active_"
           "index执行激活convert、Bond资源、端口时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure219::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure219::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure219::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：convert_bond_port_id_to_active_index，Invalid primary chip_id:。";
}

std::string UrmaFailure219::GetId() const
{
    return "urma_219";
}
} // namespace diag
