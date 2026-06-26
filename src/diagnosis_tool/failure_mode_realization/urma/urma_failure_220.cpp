#include "urma_failure_220.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure220> g_urma("urma_220");

bool UrmaFailure220::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("convert_bond_port_id_to_active_index") != std::string::npos &&
           message.find("Invalid port id, chip_id:") != std::string::npos &&
           message.find(", port_idx:") != std::string::npos;
}

std::string UrmaFailure220::GetName() const
{
    return "convert、Bond资源、端口状态不满足要求导致激活convert、Bond资源、端口失败";
}

std::string UrmaFailure220::GetRootCauseDesc() const
{
    return "convert_bond_port_id_to_active_"
           "index执行激活convert、Bond资源、端口时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure220::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure220::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure220::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：convert_bond_port_id_to_active_index，Invalid port id, chip_id:，, "
           "port_idx:。";
}

std::string UrmaFailure220::GetId() const
{
    return "urma_220";
}
} // namespace diag
