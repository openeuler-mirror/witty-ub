#include "urma_failure_021.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure021> g_urma("urma_021");

bool UrmaFailure021::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_provider_bond_uninit") != std::string::npos &&
           message.find("Provider Bond register ops not registered.") != std::string::npos;
}

std::string UrmaFailure021::GetName() const
{
    return "provider、Bond资源、uninit状态不满足要求导致providerprovider、Bond资源、uninit失败";
}

std::string UrmaFailure021::GetRootCauseDesc() const
{
    return "urma_provider_bond_"
           "uninit执行providerprovider、Bond资源、uninit时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure021::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure021::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure021::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_provider_bond_uninit，Provider Bond register ops not registered.。";
}

std::string UrmaFailure021::GetId() const
{
    return "urma_021";
}
} // namespace diag
