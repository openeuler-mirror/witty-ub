#include "urma_failure_560.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure560> g_urma("urma_560");

bool UrmaFailure560::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfs") != std::string::npos &&
           message.find("jfs still actived, please deactived first") != std::string::npos;
}

std::string UrmaFailure560::GetName() const
{
    return "JFS状态不满足要求导致释放JFS失败";
}

std::string UrmaFailure560::GetRootCauseDesc() const
{
    return "urma_free_jfs执行释放JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure560::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure560::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure560::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfs，jfs still actived, please deactived first。";
}

std::string UrmaFailure560::GetId() const
{
    return "urma_560";
}
} // namespace diag
