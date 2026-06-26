#include "urma_failure_448.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure448> g_urma("urma_448");

bool UrmaFailure448::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfc") != std::string::npos &&
           message.find("jfc still actived, please deactived first") != std::string::npos;
}

std::string UrmaFailure448::GetName() const
{
    return "JFC状态不满足要求导致释放JFC失败";
}

std::string UrmaFailure448::GetRootCauseDesc() const
{
    return "urma_free_jfc执行释放JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure448::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure448::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure448::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfc，jfc still actived, please deactived first。";
}

std::string UrmaFailure448::GetId() const
{
    return "urma_448";
}
} // namespace diag
