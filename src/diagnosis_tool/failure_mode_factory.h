#pragma once
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "failure_mode.h"

namespace diag {

class FailureModeFactory {
public:
    using Creator = std::function<std::shared_ptr<FailureMode>()>;

    // 获取单例实例
    static FailureModeFactory &Instance() noexcept;

    // 注册故障模式类型
    void Register(const std::string &typeId, Creator creator) noexcept;

    // 创建故障模式实例
    std::shared_ptr<FailureMode> Create(const std::string &typeId) const noexcept;

    // 获取所有已注册的类型ID
    std::vector<std::string> GetAllTypeIds() const noexcept;

    // 检查是否已注册
    bool IsRegistered(const std::string &typeId) const noexcept;

private:
    FailureModeFactory() = default;
    std::unordered_map<std::string, Creator> m_creators;
};

// 自动注册辅助类模板，FailureMode派生类定义时必须构造该类
template <typename T>
class AutoRegister {
public:
    explicit AutoRegister(const std::string &typeId) noexcept
    {
        FailureModeFactory::Instance().Register(typeId, []() noexcept { return std::make_shared<T>(); });
    }
};
} // namespace diag