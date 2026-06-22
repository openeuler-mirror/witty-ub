#include "urma_failure_269.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure269> g_urma("urma_269");

bool UrmaFailure269::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_net_addr_list") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure269::GetName() const
{
    return "NET、ADDR、列表无效导致释放NET、ADDR、列表失败";
}

std::string UrmaFailure269::GetRootCauseDesc() const
{
    return "urma_free_net_addr_"
           "list用于释放NET、ADDR、列表，调用方传入的NET、ADDR、列表不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure269::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure269::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure269::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_net_addr_list，Invalid parameter.。";
}

std::string UrmaFailure269::GetId() const
{
    return "urma_269";
}
} // namespace diag
