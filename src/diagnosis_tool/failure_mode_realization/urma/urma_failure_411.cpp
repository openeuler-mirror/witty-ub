#include "urma_failure_411.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure411> g_urma("urma_411");

bool UrmaFailure411::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure411::GetName() const
{
    return "ret无效导致删除JFC失败";
}

std::string UrmaFailure411::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc用于删除JFC，调用方传入的ret不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure411::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure411::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure411::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc，Invalid parameter。";
}

std::string UrmaFailure411::GetId() const
{
    return "urma_411";
}
} // namespace diag
